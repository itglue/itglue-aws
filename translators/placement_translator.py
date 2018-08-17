import translators.base_translator


class PlacementTranslator(translators.base_translator.BaseTranslator):
    FIELDS = ['name']

    def _name(self):
        return self.data.get('AvailabilityZone')
