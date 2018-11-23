import os
from import_ec2 import import_ec2_instances
from import_workspace import import_workspaces
from itglue_adapter import get_organization
import logging

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def ec2_handler(event, context):
    organization = get_org()
    instance_id = event['detail']['instance-id']
    logger.info(
        'Invoked Function ARN: %s Name of the executing Lambda function: %s Instance ID: %s',
        context.invoked_function_arn,
        context.log_group_name,
        instance_id
    )
    return import_ec2_instances(organization, instance_id=instance_id)


def workspace_handler(event, context):
    organization = get_org()
    logger.info(
        'Invoked Function ARN: %s Name of the executing Lambda function: %s Resource: %s',
        context.invoked_function_arn,
        context.log_group_name,
        event['resources']
    )
    return import_workspaces(organization)


def get_org():
    org_name_or_id = os.environ.get('ORGANIZATION')
    return get_organization(org_name_or_id)
