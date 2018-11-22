import os
from import_ec2 import import_ec2_instances
from import_workspace import import_workspaces
from itglue_adapter import get_organization


def ec2_handler(event, context):
    organization = get_org()
    instance_id = event['detail']['instance-id']
    print('Invoked Function ARN: {} Name of the executing Lambda function: {} Instance ID: {}'
          .format(context.invoked_function_arn, context.log_group_name, instance_id))
    return import_ec2_instances(organization, instance_id=instance_id)


def workspace_handler(event, context):
    organization = get_org()
    return import_workspaces(organization)


def get_org():
    org_name_or_id = os.environ.get('ORGANIZATION')
    return get_organization(org_name_or_id)
