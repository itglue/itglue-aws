from import_ec2 import get_organization, import_ec2_instances
import os

def handler(event, context):
    org_name_or_id = os.environ.get('ORGANIZATION')
    organization = get_organization(org_name_or_id)
    return import_ec2_instances(organization)

if __name__ == "__main__":
    handler(event={}, context=None)
