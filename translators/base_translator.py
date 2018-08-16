class BaseTranslator(object):
    FIELDS = []

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
