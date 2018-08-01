#!/usr/bin/env/python

import boto3
import ec2_translator
import placement_translator
import network_interface_translator
import itglue
from multiprocessing import Process
import argparse

BATCH_SIZE = 100


class EC2ImportError(Exception):
    pass


def get_organization(org_id_or_name):
    try:  # Try to cast the organization argument into an int to search by ID
        org_id = int(org_id_or_name)
        return itglue.Organization.find(org_id)
    except ValueError:  # Organization argument is not a valid int, attempt to search by name
        org_name = org_id_or_name
        orgs = itglue.Organization.filter(name=org_name)
        if not orgs:
            raise EC2ImportError('Organization with name {} not found'.format(org_name))
        return orgs[0]


def import_ec2_instances(organization, import_locations=True, instance_id=None):
    active_status = itglue.ConfigurationStatus.first_or_create(name='Active')
    inactive_status = itglue.ConfigurationStatus.first_or_create(name='Inactive')
    ec2_type = itglue.ConfigurationType.first_or_create(name='EC2')

    # create a list to keep all processes
    processes = []

    kwargs = {
        'organization': organization,
        'conf_type': ec2_type,
        'active_status': active_status,
        'inactive_status': inactive_status
    }

    if instance_id:
        instance = get_instances(instance_id)
        process = configure_instance(instance, import_locations, organization.id, kwargs)
        process.start()
        process.join()
    else:
        instances = get_instances()
        for instance in instances:
            process = configure_instance(instance, import_locations, organization.id, kwargs)
            processes.append(process)
        batch_start_processes(processes)


def batch_start_processes(processes):
    counter = 0
    total_count = counter + BATCH_SIZE
    while counter < len(processes):
        if total_count > len(processes):
            total_count = len(processes)
        for index in range(counter, total_count):
            processes[index].start()
        for index in range(counter, total_count):
            processes[index].join()
        counter += BATCH_SIZE
        total_count = counter + BATCH_SIZE


def get_instances(instance_id=None):
    ec2 = boto3.resource('ec2')
    if instance_id:
        instance = ec2.Instance(instance_id)
        return instance
    return ec2.instances.all()


def configure_instance(instance, import_locations, organization_id, kwargs):
    locations_dict = {}
    kwargs['instance'] = instance
    if import_locations:
        location_translator = placement_translator.PlacementTranslator(instance.placement)
        location_name = location_translator.translate('name')
        if locations_dict.get(location_name):
            kwargs['location'] = locations_dict[location_name]
        else:
            location_attributes = location_translator.translated
            location = itglue.Location.first_or_create(organization_id=organization_id, **location_attributes)
            locations_dict[location_name] = location
            kwargs['location'] = location
    process = Process(target=update_configuration_and_interfaces, kwargs=kwargs)
    return process


def update_configuration_and_interfaces(organization, instance, conf_type, active_status, inactive_status, location=None):
    configuration = update_or_create_configuration(
        instance=instance,
        location=location,
        organization=organization,
        conf_type=conf_type,
        active_status=active_status,
        inactive_status=inactive_status
    )
    for interface in instance.network_interfaces:
        primary = instance.private_ip_address == interface.private_ip_address
        update_or_create_config_interface(interface, configuration, primary=primary)


def update_or_create_configuration(instance, location, organization, conf_type, active_status, inactive_status):
    instance_attributes = ec2_translator.EC2Translator(
        instance,
        active_status_id=active_status.id,
        inactive_status_id=inactive_status.id
    ).translated
    serial_number = instance_attributes.get('serial_number')
    if serial_number:
        configuration = itglue.Configuration.find_by(organization_id=organization.id, serial_number=serial_number)

    configuration = configuration or itglue.Configuration(organization_id=organization.id)
    location_id = location.id if location else None
    configuration.set_attributes(location_id=location_id, configuration_type_id=conf_type.id, **instance_attributes)
    configuration.save()
    return configuration


def update_or_create_config_interface(interface, configuration, primary=False):
    interface_attributes = network_interface_translator.NetworkInterfaceTranslator(interface).translated
    config_interface = itglue.ConfigurationInterface.first_or_initialize(
        parent=configuration,
        configuration_id=configuration.id,
        primary_ip=interface.private_ip_address
    )
    config_interface.set_attributes(primary=primary, **interface_attributes)
    config_interface.save()
    return config_interface


# Command-line functions
def main():
    args = get_args()
    import_locations = args.import_locations
    id = args.instance_id
    if args.add_all and id:
        id = None
    organization = get_organization(args.organization)
    import_ec2_instances(organization, import_locations=import_locations, instance_id=id)
    return True


def get_args():
    parser = argparse.ArgumentParser(
        description='Import EC2 instances as Configurations into an IT Glue Organization')
    parser.add_argument(
        'organization',
        metavar='ORG_ID_OR_NAME',
        type=str,
        help='The ID or NAME of the parent organization'
    )
    parser.add_argument(
        '-il', '--import-locations',
        action='store_true',
        help='Import EC2 placements as IT Glue Locations'
    )
    parser.add_argument(
        '-id', '--instance-id',
        type=str,
        help='ID of the instance to be created'
    )
    parser.add_argument(
        '--add-all',
        action='store_true',
        help='add all the ec2 instances, will override instance_id'
    )
    args = parser.parse_args()
    if not args.add_all and not args.instance_id:
        parser.error('Must provide an instance ID or turn on --add-all flag')
    return args


if __name__ == "__main__":
    main()
