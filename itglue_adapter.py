import itglue
import translators.network_interface_translator


class ImportError(Exception):
    pass


def get_organization(org_id_or_name):
    try:  # Try to cast the organization argument into an int to search by ID
        org_id = int(org_id_or_name)
        return itglue.Organization.find(org_id)
    except ValueError:  # Organization argument is not a valid int, attempt to search by name
        org_name = org_id_or_name
        orgs = itglue.Organization.filter(name=org_name)
        if not orgs:
            raise ImportError('Organization with name {} not found'.format(org_name))
        return orgs[0]


def update_or_create_configuration(resource, organization, conf_type, location=None):
    filters = {'organization_id': organization.id,
               'name': resource.get('name')
               }
    if resource.get('serial_number'):
        filters['serial_number'] = resource.get('serial_number')
    configuration = itglue.Configuration.find_by(**filters) or itglue.Configuration(organization_id=organization.id)
    if location:
        location_id = location.id
    configuration.set_attributes(location_id=location_id, configuration_type_id=conf_type.id, **resource)
    configuration.save()
    return configuration


def update_or_create_config_interface(interface, configuration, primary=False):
    interface_attributes = translators.network_interface_translator.NetworkInterfaceTranslator(interface).translated
    config_interface = itglue.ConfigurationInterface.first_or_initialize(
        parent=configuration,
        configuration_id=configuration.id,
        primary_ip=interface.private_ip_address
    )
    config_interface.set_attributes(primary=primary, **interface_attributes)
    config_interface.save()


def get_or_create_config_statuses():
    active_status = itglue.ConfigurationStatus.first_or_create(name='Active')
    inactive_status = itglue.ConfigurationStatus.first_or_create(name='Inactive')
    return active_status, inactive_status
