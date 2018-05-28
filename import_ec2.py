#!/usr/bin/env/python

import boto3
import translator
from itglue import Record
from multiprocessing import Process
import argparse

class EC2ImportError(Exception):
    pass

def import_ec2_instances(organization, ignore_locations=False):
    instances = get_instances()
    active_status = Record.first_or_create('configuration_statuses', name='Active')
    inactive_status = Record.first_or_create('configuration_statuses', name='Inactive')
    ec2_type = Record.first_or_create('configuration_types', name='EC2')
    locations = Record.get('locations', parent=organization) if not ignore_locations else []
    for instance in instances:
        kwargs = {
            'organization': organization,
            'instance': instance,
            'conf_type': ec2_type,
            'active_status': active_status,
            'inactive_status': inactive_status,
            'locations': locations,
            'ignore_locations': ignore_locations
        }
        process = Process(target=update_configurations, kwargs=kwargs)
        process.start()

def get_organization(org_id_or_name):
    try: # Try to cast the organization argument into an int to search by ID
        org_id = int(org_id_or_name)
        return Record.find('organizations', id=org_id)
    except ValueError: # Organization argument is not a valid int, attempt to search by name
        org_name = org_id_or_name
        orgs = Record.filter('organizations', name=org_name)
        if not orgs:
            raise EC2ImportError('Organization with name {} not found'.format(org_name))
        return orgs[0]

def update_configurations(organization, instance, conf_type, active_status, inactive_status, locations, ignore_locations=False):
    if ignore_locations:
        location = None
    else:
        location = get_or_create_location(instance.placement, locations, organization)
    configuration = update_or_create_configuration(
        instance=instance,
        location=location,
        organization=organization,
        conf_type=conf_type,
        active_status=active_status,
        inactive_status=inactive_status
    )
    for interface in instance.network_interfaces:
        update_or_create_config_interface(interface, configuration)

def get_instances():
    ec2 = boto3.resource('ec2')
    return ec2.instances.all()

def get_or_create_location(placement, locations, organization):
    location_translator = translator.PlacementTranslator(placement)
    location_name = location_translator.translate('name')
    matching_locations = [location for location in locations if location.get_attr('name') == location_name]
    if matching_locations:
        return matching_locations[0]
    else:
        location_attributes = location_translator.translated
        location = Record.first_or_create('locations', organization_id=organization.id, **location_attributes)
        return location
    # location_attributes = translator.PlacementTranslator(placement).translated
    # return Record.first_or_create('locations', organization_id=organization.id, **location_attributes)

def update_or_create_configuration(instance, location, organization, conf_type, active_status, inactive_status):
    instance_attributes = translator.EC2Translator(
        instance,
        active_status_id=active_status.id,
        inactive_status_id=inactive_status.id
    ).translated
    serial_number = instance_attributes.get('serial_number')
    if serial_number:
        configuration = Record.find_by('configurations', organization_id=organization.id, serial_number=serial_number)
    configuration = configuration or Record('configurations', organization_id=organization.id)
    location_id = location.id if location else None
    configuration.set_attributes(location_id=location_id, configuration_type_id=conf_type.id, **instance_attributes)
    configuration.save()
    return configuration


def update_or_create_config_interface(interface, configuration):
    interface_ip = interface.private_ip_address
    interface_attributes = translator.NetworkInterfaceTranslator(interface).translated
    config_interface = Record.first_or_initialize(
        'configuration_interfaces',
        parent=configuration,
        configuration_id=configuration.id,
        primary_ip=interface_ip
    )
    primary = configuration.get_attr('primary_ip') == interface_ip
    config_interface.set_attributes(primary=primary, **interface_attributes)
    config_interface.save()
    return config_interface

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

