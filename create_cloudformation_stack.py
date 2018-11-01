import argparse
import boto3
import botocore
import datetime
import json
import ruamel.yaml

RESOURCES = ['workspace',
             'ec2'
             ]


class CfnError(Exception):
    pass


def _load_yaml_files(resource_list):
    """Generates a complete Cloudformation YAML template with specified params

    Each specified resource (e.g. ec2) has its own template YAML that contains
    a Lambda function, specific role and policy

    base.yaml - contains all the basic details and resources required of a Cloudformation
    """
    yaml = ruamel.yaml.YAML()
    with open('./templates/base.yaml') as base:
        base_cfn = yaml.load(base)
    for resource in resource_list:
        with open(f'./templates/{resource}.yaml', 'r') as file:
            resource_template = yaml.load(file)
            updated_template = _load_resources(base_cfn, resource_template['Resources'])
            print(f'{resource} template added')
    today_date = str(datetime.datetime.now())
    with open(f'./cfn_template_{today_date}.yml', 'w') as cfn_template:
        yaml.dump(updated_template, cfn_template)
    print('Cloudformation template created')
    return cfn_template.name


def _load_resources(base_cfn, yaml_properties):
    for resource in yaml_properties:
        resource_block = yaml_properties[resource]
        base_cfn['Resources'].update({resource: resource_block})
    return base_cfn


def _update_or_create_stack(cf, cfn_params, stack_name):
    """Creates a Cloudformation stack or updates an existing stack of the same name"""
    try:
        if _stack_exists(cf, stack_name):
            print(f'Updating {stack_name}')
            stack_result = cf.update_stack(**cfn_params)
            waiter = cf.get_waiter('stack_update_complete')
        else:
            print(f'Creating {stack_name}')
            stack_result = cf.create_stack(**cfn_params)
            waiter = cf.get_waiter('stack_create_complete')
        print("Waiting for stack to be ready...")
        waiter.wait(StackName=stack_name)
    except botocore.exceptions.ClientError as error:
        error_message = error.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print("No changes on the stack")
        else:
            raise
    else:
        complete_cfn = cf.describe_stacks(StackName=stack_result['StackId'])
        print(json.dumps(complete_cfn, indent=2, default=_json_serial))


def _stack_exists(cf, stack_name):
    paginator = cf.get_paginator('list_stacks')
    for page in paginator.paginate():
        for stack in page['StackSummaries']:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName']:
                return True
    return False


def _parse_parameters():
    try:
        with open('./parameters.json', 'r') as param_file:
            return json.load(param_file)
    except OSError:
        raise


def _match_resources(resources):
    new_resources = []
    for resource in resources:
        if resource.lower() not in RESOURCES:
            return False
        new_resources.append(resource.lower())
    return new_resources


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type is not serializable")


def main():
    cf = boto3.client('cloudformation')
    args = get_args()
    if args.add_all:
        template = _load_yaml_files(RESOURCES)
    else:
        resources = _match_resources(args.resources)
        if resources:
            template = _load_yaml_files(resources)
        else:
            raise ValueError(f'Resources supported are: {RESOURCES}')
    params = _parse_parameters()
    with open(template, 'r') as cfn_template:
        cfn_params = {
            'StackName': args.stack_name,
            'TemplateBody': cfn_template.read(),
            'Parameters': params,
            'Capabilities': ['CAPABILITY_IAM']
        }
    _update_or_create_stack(cf, cfn_params, args.stack_name)


def get_args():
    parser = argparse.ArgumentParser(
        description='Create a Cloudformation stack importing specified AWS resources')
    parser.add_argument(
        'stack_name',
        type=str,
        help='Enter the Cloudformation stack name'
    )
    parser.add_argument(
        '--add-all',
        action='store_true',
        help='Adds all the resources in AWS'
    )
    parser.add_argument(
        '-r', '--resources',
        nargs='+',
        help=f'Resources you would like to import from AWS. Currently supports: {RESOURCES}'
    )
    args = parser.parse_args()
    if not (args.resources or args.add_all):
        parser.error('Must provide a resource to import or turn on --add-all flag')
    return args


if __name__ == '__main__':
    main()
