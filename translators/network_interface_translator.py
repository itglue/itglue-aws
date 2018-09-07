import translators.base_translator


class NetworkInterfaceTranslator(translators.base_translator.BaseTranslator):
    """Translates a Network Interface from an EC2 Instance to IT Glue Configuration Interface"""
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
