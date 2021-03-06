import argparse
import boto3
import botocore
import datetime
from jinja2 import Environment, FileSystemLoader
import json
import os
import ruamel.yaml

RESOURCES = ['workspace',
             'ec2'
             ]

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class CfnError(Exception):
    pass


def _load_yaml_files(stack_name, resource_list):
    """Generates a complete Cloudformation YAML template with specified params

    Each specified resource (e.g. ec2) has its own template YAML that contains
    a Lambda function, specific role and policy

    base.yaml - contains all the basic details and resources required of a Cloudformation
    """
    yaml = ruamel.yaml.YAML()
    with open(f'{DIR_PATH}/templates/base.yaml') as base:
        base_cfn = yaml.load(base)
    for resource in resource_list:
        function_name = f'{stack_name}{resource}SyncFunction'
        with open(f'{DIR_PATH}/templates/{resource}.yaml', 'r') as file:
            new_file = _update_resource_function_name(resource, function_name)
            resource_template = yaml.load(new_file)
            updated_template = _load_resources(base_cfn, resource_template['Resources'])
            print(f'{resource} template added')
    today_date = str(datetime.datetime.now())
    with open(f'{DIR_PATH}/cfn_template_{today_date}.yml', 'w') as cfn_template:
        yaml.dump(updated_template, cfn_template)
    print('Cloudformation template created')
    return cfn_template.name


def _update_resource_function_name(resource, function_name):
    env = Environment(loader=FileSystemLoader(DIR_PATH))
    template = env.get_template(f'templates/{resource}.yaml')
    updated_file = template.render(functionName=function_name)
    return updated_file


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
            raise error
    else:
        complete_cfn = cf.describe_stacks(StackName=stack_name)
        print(json.dumps(complete_cfn, indent=2, default=_json_serial))


def _stack_exists(cf, stack_name):
    try:
        cf.describe_stacks(StackName=stack_name)
        return True
    except botocore.exceptions.ClientError as e:
        # If the stack was not found, returns ValidationError code
        if e.response['Error']['Code'] != 'ValidationError':
            raise e
        return False


def _parse_parameters():
    with open(f'{DIR_PATH}/parameters.json', 'r') as param_file:
        return json.load(param_file)


def _match_resources(resources):
    new_resources = []
    for resource in resources:
        lowercase_resource = resource.lower()
        if lowercase_resource not in RESOURCES:
            return False
        new_resources.append(lowercase_resource)
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
        template = _load_yaml_files(args.stack_name, RESOURCES)
    else:
        resources = _match_resources(args.resources)
        if resources:
            template = _load_yaml_files(args.stack_name, resources)
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
        help=f'Resources you would like to import from AWS separated by spaces. Currently supports: {RESOURCES}'
    )
    args = parser.parse_args()
    if not (args.resources or args.add_all):
        parser.error('Must provide a resource to import or turn on --add-all flag')
    return args


if __name__ == '__main__':
    main()
