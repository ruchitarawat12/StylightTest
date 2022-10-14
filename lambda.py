import boto3
from tabulate import tabulate
from datetime import date, timedelta
import os
import pathlib


# call to cost explorer API to get the cost of resources
def get_cost_data():
    start_date = date.today() - timedelta(days=7)
    client = boto3.client('ce')
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': '{0}'.format(start_date),
            'End': '{0}'.format(date.today())
        },
        Granularity='MONTHLY',
        Filter={
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': ["Amazon Elastic Compute Cloud - Compute", "Amazon Relational Database Service"]
            }
        },
        Metrics=[
            'BlendedCost',
        ],
        GroupBy=[
            {
                'Type': 'TAG',
                'Key': 'Name'
            },
        ],
    )
    return response


# check the resources costing more than expected weekly_budget
def compare_expensive_resource(weekly_budget):
    budget = weekly_budget
    expensive_resources = []
    data = get_cost_data()
    resource_cost_data = data["ResultsByTime"][0]["Groups"]
    for i in resource_cost_data:
        resource_cost = float(i["Metrics"]["BlendedCost"]["Amount"])
        if resource_cost > budget:
            resource_name = i["Keys"][0].split("$")[1]
            expensive_resources.append([resource_name, resource_cost])
    return expensive_resources


def lambda_handler(event, context):
    expensive_resources = compare_expensive_resource(int(os.environ["weekly_budget"]))
    sns_client = boto3.client('sns', region_name='us-east-1')
    snsArn = os.environ["sns_arn"]
    data = tabulate(expensive_resources, headers=['Resource_Name', 'Resource_cost'], tablefmt='orgtbl')
    response = sns_client.publish(
        TopicArn=snsArn,
        Message=data,
        Subject='Hello'
    )

    s3_client = boto3.client('s3')
    data = tabulate(expensive_resources, headers=['Resource_Name', 'Resource_cost'], tablefmt='orgtbl')
    expense_report =  '/tmp/expenses_report' + '(' + str(date.today()) + ')' + ".txt"
    with open(expense_report, 'w') as f:
        f.write(data)
        f.close()
    file_name = os.path.join(pathlib.Path(__file__).parent.resolve(), expense_report)
    s3_bucket_name = os.environ["bucket_name"]
    object_name = expense_report
    s3_client.upload_file(file_name, s3_bucket_name, object_name)

