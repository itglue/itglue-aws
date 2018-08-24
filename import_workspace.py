import boto3
import translators.workspace_translator
import itglue_adapter
import itglue
from multiprocessing import Process


class WorkspaceImportError(Exception):
    pass


def get_workspaces(workspace_id=None):
    workspace_client = boto3.client('workspaces')
    if workspace_id:
        workspace = workspace_client.describe_workspaces(WorkspaceIds=[workspace_id])
        return workspace.get('Workspaces')[0]
    # create list of workspaces
    workspaces = []
    paginator = workspace_client.get_paginator('describe_workspaces')

    # create workspace page iterator
    response_iterator = paginator.paginate(
        PaginationConfig={
            'PageSize': 10,
            'StartingToken': None
        }
    )
    for page in response_iterator:
        workspaces.extend(page['Workspaces'])
    return workspaces


def import_workspaces(organization, workspace_id=None, contact=True):
    workspace_type = itglue.ConfigurationType.first_or_create(name='Workspace')
    active_status, inactive_status = itglue_adapter.get_or_create_config_statuses()

    processes = []

    if workspace_id:
        workspace = get_workspaces(workspace_id)
        workspace_attributes = translate_workspaces(workspace, active_status, inactive_status)
        update_configuration_and_interfaces(workspace, workspace_attributes, organization, workspace_type)
    else:
        workspaces = get_workspaces()
        for workspace in workspaces:
            workspace_attributes = translate_workspaces(workspace, active_status, inactive_status)
            process = Process(target=update_configuration_and_interfaces, args=(workspace_attributes, organization, workspace_type))
            processes.append(process)
        print("finished importing workspaces")
    itglue_adapter.batch_start_processes(processes)


def translate_workspaces(workspace, active_status, inactive_status):
    workspace_attributes = translators.workspace_translator.WorkspaceTranslator(
        workspace,
        active_status_id=active_status.id,
        inactive_status_id=inactive_status.id
    )
    return workspace_attributes.translated


def update_configuration_and_interfaces(workspace_attributes, organization, workspace_type):
    configuration = itglue_adapter.update_or_create_configuration(
        resource=workspace_attributes,
        organization=organization,
        conf_type=workspace_type
    )
    if workspace_attributes.get('ip_address'):
        itglue_adapter.update_or_create_config_interface(workspace_attributes, configuration, primary=True, ip_address=workspace_attributes.get('ip_address'))
