#!/usr/bin/env/python

import boto3
import translator
import itglue
from multiprocessing import Process
import argparse

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

def import_ec2_instances(organization, ignore_locations=False):
    instances = get_instances()
    active_status = itglue.ConfigurationStatus.first_or_create(name='Active')
    inactive_status = itglue.ConfigurationStatus.first_or_create(name='Inactive')
    ec2_type = itglue.ConfigurationType.first_or_create(name='EC2')

    # create a dict to memoize the locations
    locations_dict = {}

    # create a list to keep all processes
    processes = []

    for instance in instances:
        kwargs = {
            'organization': organization,
            'instance': instance,
            'conf_type': ec2_type,
            'active_status': active_status,
            'inactive_status': inactive_status
        }
        if not ignore_locations:
            location_translator = translator.PlacementTranslator(instance.placement)
            location_name = location_translator.translate('name')
            if locations_dict.get(location_name):
                kwargs['location'] = locations_dict[location_name]
            else:
                location_attributes = location_translator.translated
                location = itglue.Location.first_or_create(organization_id=organization.id, **location_attributes)
                locations_dict[location_name] = location
                kwargs['location'] = location
        process = Process(target=update_configuration_and_interfaces, kwargs=kwargs)
        processes.append(process)

    # start all processes
    for process in processes:
        process.start()

    # make sure that all processes have finished
    for process in processes:
        process.join()

def get_instances():
    ec2 = boto3.resource('ec2')
    return ec2.instances.all()

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
    instance_attributes = translator.EC2Translator(
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
    interface_attributes = translator.NetworkInterfaceTranslator(interface).translated
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
    args = parse_args()
    ignore_locations = args.ignore_locations
    organization = get_organization(args.organization)
    import_ec2_instances(organization, ignore_locations=ignore_locations)
    return True

def parse_args():
    parser = argparse.ArgumentParser(
        description='Import EC2 instances as Configurations into an IT Glue Organization')
    parser.add_argument(
        'organization',
        metavar='ORG_ID_OR_NAME',
        type=str,
        help='The ID or NAME of the parent organization'
    )
    parser.add_argument(
        '-il', '--ignore-locations',
        action='store_true',
        help='Do not import EC2 placements as IT Glue Locations'
    )
    return parser.parse_args()

if __name__ == "__main__":
    main()

