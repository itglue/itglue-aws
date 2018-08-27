from import_ec2 import import_ec2_instances
from itglue_adapter import get_organization
import os


def handler(event, context):

    org_name_or_id = os.environ.get('ORGANIZATION')
    organization = get_organization(org_name_or_id)
    instance_id = event['detail']['instance-id']
    return import_ec2_instances(organization, instance_id=instance_id)


if __name__ == "__main__":
    handler(event={}, context=None)
