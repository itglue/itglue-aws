from import_ec2 import get_organization, import_ec2_instances

def handler(event, context):
    organization = get_organization('IT Glue AWS')
    return import_ec2_instances(organization)

if __name__ == "__main__":
    handler(event={}, context=None)
