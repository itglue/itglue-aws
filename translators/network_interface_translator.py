import base_translator


class NetworkInterfaceTranslator(base_translator.BaseTranslator):
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
