#!/usr/bin/env/python

import boto3
import translators.ec2_translator
import translators.placement_translator
import itglue
import importer_wrapper
from multiprocessing import Process
import argparse

BATCH_SIZE = 100


class EC2ImportError(Exception):
    pass


def import_ec2_instances(organization, import_locations=True, instance_id=None):
    ec2_type = itglue.ConfigurationType.first_or_create(name='EC2')
    active_status, inactive_status = importer_wrapper.get_or_create_config_statuses()

    # create a list to keep all processes
    processes = []

    kwargs = {
        'organization': organization,
        'conf_type': ec2_type
    }

    if instance_id:
        instance = get_instances(instance_id)
        instance_kwargs = configure_instance(instance, import_locations, organization.id, active_status, inactive_status, kwargs)
        update_configuration_and_interfaces(instance, **instance_kwargs)
    else:
        instances = get_instances()
        for instance in instances:
            instance_kwargs = configure_instance(instance, import_locations, organization.id, active_status, inactive_status, kwargs)
            process = Process(target=update_configuration_and_interfaces, args=(instance,), kwargs=instance_kwargs)
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


def configure_instance(instance, import_locations, organization_id, active_status, inactive_status, kwargs):
    kwargs['translated_instance'] = translate_instances(instance, active_status, inactive_status)
    if import_locations:
        location_attributes = translators.placement_translator.PlacementTranslator(instance.placement).translated
        location_attributes['organization_id'] = organization_id
        location = itglue.Location.first_or_create(parent=kwargs['organization'], **location_attributes)
        kwargs['location'] = location
    return kwargs


def update_configuration_and_interfaces(instance, organization, translated_instance, conf_type, location=None):
    configuration = importer_wrapper.update_or_create_configuration(
        resource=translated_instance,
        location=location,
        organization=organization,
        conf_type=conf_type
    )
    for interface in instance.network_interfaces:
        primary = instance.private_ip_address == interface.private_ip_address
        importer_wrapper.update_or_create_config_interface(interface, configuration, primary=primary)


def translate_instances(instance, active_status, inactive_status):
    instance_attributes = translators.ec2_translator.EC2Translator(
        instance,
        active_status_id=active_status.id,
        inactive_status_id=inactive_status.id
    )
    return instance_attributes.translated


# Command-line functions
def main():
    args = get_args()
    import_locations = args.import_locations
    id = args.instance_id
    if args.add_all and id:
        id = None
    organization = importer_wrapper.get_organization(args.organization)
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
