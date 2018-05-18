#!/usr/bin/env/python

import boto3
import translator
from record import Record
import argparse

def main(organization):
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.limit(1)
    active_status = Record('configuration_statuses', name='Active')
    active_status.first_or_create('name')
    inactive_status = Record('configuration_statuses', name='Inactive')
    inactive_status.first_or_create('name')
    ec2_type = Record('configuration_types', name='EC2')
    ec2_type.first_or_create('name')
    for instance in instances:
        location_attributes = translator.PlacementTranslator(instance.placement).translated
        location = Record('locations', organization_id=organization.id, **location_attributes)
        location.first_or_create('name')
        instance_attributes = translator.EC2Translator(
            instance,
            active_status_id=active_status.id,
            inactive_status_id=inactive_status.id
        ).translated
        configuration = Record(
            'configurations',
            organization_id=organization.id,
            location_id=location.id,
            configuration_type_id=ec2_type.id,
            **instance_attributes
        )
        primary_ip = instance.private_ip_address
        interfaces = []
        for interface in instance.network_interfaces:
            primary = primary_ip == interface.private_ip_address
            interface_attributes = translator.NetworkInterfaceTranslator(interface).translated
            config_interface = Record('configuration_interfaces', primary=primary, **interface_attributes)
            interfaces.append(config_interface)
        configuration.first_or_create('serial_number', configuration_interfaces=interfaces)

    print("Done!")

def parse_args():
    parser = argparse.ArgumentParser(description='Import EC2 instances as Configurations into an IT Glue Organization')
    parser.add_argument('organization', metavar='ORG_ID_OR_NAME',
                        type=str, help='The ID or NAME of the parent organization')
    args = parser.parse_args()
    org_id_or_name = args.organization
    try:
        org_id = int(org_id_or_name)
        organization = Record.find('organizations', id=org_id)
    except ValueError:
        org_name = org_id_or_name
        orgs = Record.filter('organizations', name=org_name)
        try:
            organization = orgs[0]
        except IndexError:
            parser.error(
                'Organization with name {} not found'.format(org_name))
    return {'organization': organization}

if __name__ == "__main__":
    args = parse_args()
    main(**args)

