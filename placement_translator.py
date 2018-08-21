import base_translator


class PlacementTranslator(base_translator.BaseTranslator):
    FIELDS = ['name']

    def _name(self):
        return self.data.get('AvailabilityZone')
