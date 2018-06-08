import json

class TranslatorBase(object):
    FIELDS = []
    RELATIONSHIPS = []

    class TranslatorError(Exception):
        pass

    def __init__(self, data, **options):
        self.data = data
        self.options = options
        self.attributes = {}

    @property
    def translated(self):
        for attribute in self.FIELDS:
            if self.attributes.get(attribute) is None:
                self.translate(attribute)
        return self.attributes

    def translate(self, field):
        if not self.attributes.get(field):
            self.attributes[field] = getattr(self, '_{}'.format(field))()
        return self.attributes[field]

    def _format_notes(self, notes_dict):
        notes_list = []
        for key, value in notes_dict.items():
            notes_list.append('{}: \t{}'.format(key, value))
        return '\n'.join(notes_list)


class EC2Translator(TranslatorBase):
    FIELDS = [
        'name',
        'serial_number',
        'purchased_at',
        'configuration_status_id',
        'mac_address',
        'notes'
    ]
    RELATIONSHIPS = [
        'configuration_interfaces'
    ]

    def primary_interface(self):
        for interface in self.data.network_interfaces:
            if self.data.private_ip_address == interface.private_ip_address:
                return interface

    def _name(self):
        for tag in self.data.tags or []:
            if tag['Key'] == 'Name' and tag.get('Value'):
                return tag['Value']
        # Fallback in case the EC2 instance does not have a name (required)
        if self.data.key_name:
            return self.data.key_name
        elif self.data.instance_id:
            return self.data.instance_id
        return '[Unnamed Instance]'

    def _serial_number(self):
        return self.data.instance_id

    def _purchased_at(self):
        return self.data.launch_time.strftime('%Y-%m-%d')

    def _configuration_status_id(self):
        state_name = self.data.state['Name']
        active_status_id = self.options.get('active_status_id')
        inactive_status_id = self.options.get('inactive_status_id')
        if not active_status_id or not inactive_status_id:
            raise self.TranslatorError('Both an active_status_id and an inactive_status_id must be provided')
        if state_name == 'running':
            return active_status_id
        else:
            return inactive_status_id

    def _mac_address(self):
        primary_ip = self.data.private_ip_address
        for interface in self.data.network_interfaces:
            if interface.private_ip_address == primary_ip:
                return interface.mac_address

    def _notes(self):
        notes_dict = {
            'key_name': self.data.key_name,
            'security_groups': ', '.join(self._security_group_names()),
            'instance_type': self.data.instance_type,
            'public_dns_name': self.data.public_dns_name,
            'private_dns_name': self.data.private_dns_name,
            'image_id': self.data.image_id,
            'availability_zone': self._availability_zone()
        }
        return self._format_notes(notes_dict)

    def _security_group_names(self):
        security_group_names = []
        for group in self.data.security_groups:
            group_name = group.get('GroupName')
            if group_name:
                security_group_names.append(group_name)
        return security_group_names

    def _availability_zone(self):
        if self.data.placement:
            return self.data.placement.get('AvailabilityZone')

class NetworkInterfaceTranslator(TranslatorBase):
    FIELDS = [
        'name',
        'ip_address',
        'notes'
    ]

    def _name(self):
        return self.data.id

    def _ip_address(self):
        return self.data.private_ip_address

    def _notes(self):
        return self._format_notes({'vpc_id': self.data.vpc_id, 'subnet_id': self.data.subnet_id})

class PlacementTranslator(TranslatorBase):
    FIELDS = ['name']

    def _name(self):
        return self.data.get('AvailabilityZone')
