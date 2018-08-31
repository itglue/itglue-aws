import argparse
import boto3
import ruamel.yaml
import os


class CfnError(Exception):
    pass

# TODO: Refactor and code clean up
def _load_yaml_files(resource_list):
    yaml = ruamel.yaml.YAML()
    with open('./templates/base.yaml') as base:
        base_cfn = yaml.load(base)
    for resource in resource_list:
        try:
            file = open('./templates/{}.yaml'.format(resource), 'r')
        except OSError:
            print('{} template file does not exist'.format(resource))
            break
        yaml_data = yaml.load(file)
        for resource_data in yaml_data['Resources']:
            base_cfn['Resources'].update({resource_data: yaml_data['Resources'][resource_data]})
        print('{} template added to Cloudformation template body'.format(resource))
    cfn_template = open('./cfn_template.yml', 'w')
    yaml.dump(base_cfn, cfn_template)
    print('Cloudformation template created')
    return cfn_template.name


def create_cfn_stack(stack_name, org_id, cfn_template, api_key, api_url):
    cloudformation = boto3.resource('cloudformation')
    template = open(cfn_template, 'r')
    cloudformation.create_stack(
        StackName=stack_name,
        TemplateBody=template.read(),
        Parameters=[
            {
                'ParameterKey': 'ITGlueAPIKey',
                'ParameterValue': api_key
            },
            {
                'ParameterKey': 'ITGlueAPIURL',
                'ParameterValue': api_url
            },
            {
                'ParameterKey': 'ITGlueOrganization',
                'ParameterValue': org_id
            }
        ],
        Capabilities=['CAPABILITY_IAM']
    )
    print('stack {} has started, monitor the progress in your AWS console'.format(stack_name))


def _stack_exists(stack_name):
    cf = boto3.client('cloudformation')
    stacks = cf.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack_name == stack['StackName']:
            return True
    return False


def main():
    args = get_args()
    # TODO: read from a param file
    itg_api_key = os.environ.get('ITGLUE_API_KEY')
    itg_api_url = os.environ.get('ITGLUE_API_URL')
    if not itg_api_key:
        raise CfnError('IT Glue API Key is required.')
    template = _load_yaml_files(args.resources)
    create_cfn_stack(args.stack_name, args.organization, template, itg_api_key, itg_api_url)


def get_args():
    parser = argparse.ArgumentParser(
        description='Create a Cloudformation stack importing specified resources')
    parser.add_argument(
        'stack_name',
        type=str,
        help='Enter the Cloudformation stack name'
    )
    parser.add_argument(
        'organization',
        metavar='ORG_ID_OR_NAME',
        type=str,
        help='Enter the name or ID of the IT Glue Organization'
    )
    parser.add_argument(
        '--add-all',
        action='store_true',
        help='Adds all the resources in AWS'
    )
    parser.add_argument(
        '-r', '--resources',
        nargs='+',
        help='Resources you would like to import from AWS. Currently supports "ec2", "workspace"'
    )
    args = parser.parse_args()
    if not args.resources:
        parser.error('Must provide a resource to import or turn on --add-all flag')
    return args


if __name__ == '__main__':
    main()
