from connection import Connection
from path_processor import PathProcessor

class Record(object):
    connection = Connection()

    class RecordError(Exception):
        pass

    def __init__(self, record_type, id=None, **attributes):
        self.record_type = record_type
        self.attributes = attributes
        self.id = id

    def __repr__(self):
        return "<{class_name} type: {type}, id: {id}, attributes: {attributes}>".format(
            class_name=self.__class__.__name__, type=self.record_type, id=self.id, attributes=self.attributes
        )

    def get_attr(self, attr_name):
        return self.attributes.get(attr_name)

    def set_attr(self, attr_name, attr_value):
        self.attributes[attr_name] = attr_value
        return attr_value

    def set_attributes(self, **attributes_dict):
        for attr_name, attr_value in attributes_dict.iteritems():
            self.set_attr(attr_name, attr_value)
        return self

    def save(self):
        if self.id:
            return self.update()
        else:
            return self.create()

    def create(self, parent=None, **relationships):
        if self.id:
            raise self.RecordError('cannot create a record with an existing ID')
        data = self.__class__._process_request(
            self.record_type,
            self.connection.post,
            parent=parent,
            payload=self.payload(),
            relationships=self.relationships_payload(relationships)
        )
        return self._reload(data)

    def update(self, parent=None):
        if not self.id:
            raise self.RecordError('cannot update a record without an ID')
        data = self.__class__._process_request(
            self.record_type,
            self.connection.patch,
            parent=parent,
            id=self.id,
            payload=self.payload()
        )
        return self._reload(data)

    def _reload(self, data):
        self.id = data['id']
        self.attributes = data['attributes']
        self.record_type = data['type']
        return self

    def payload(self):
        payload = {'type': self.record_type, 'attributes': self.attributes }
        if self.id:
            payload['id'] = self.id
        return payload

    @staticmethod
    def relationships_payload(relationships):
        rel_payload = {}
        for rel_name, rel_items in relationships.iteritems():
            rel_payload[rel_name] = list(map(lambda rel_item: rel_item.payload(), rel_items))
        return rel_payload

    @classmethod
    def get(cls, record_type, parent=None):
        data = cls._process_request(record_type, cls.connection.get, parent=parent)
        return cls._load_resources(data)

    @classmethod
    def filter(cls, record_type, parent=None, **filters):
        data = cls._process_filter_request(record_type, parent, **filters)
        return cls._load_resources(data)

    @classmethod
    def find(cls, record_type, id, parent=None):
        data = cls._process_request(record_type, cls.connection.get, parent=parent, id=id)
        return cls._load_resource(data)

    @classmethod
    def first_or_create(cls, record_type, parent=None, **attributes):
        existing_record = cls.find_by(record_type, **attributes)
        if existing_record:
            return existing_record
        return cls(record_type, **attributes).create()

    @classmethod
    def first_or_initialize(cls, record_type, parent=None, **attributes):
        existing_record = cls.find_by(record_type, parent, **attributes)
        if existing_record:
            return existing_record
        return cls(record_type, **attributes)

    @classmethod
    def find_by(cls, record_type, parent=None, **attributes):
        if not attributes:
            raise cls.RecordError('at least one attribute must be provided')
        print('attributes', attributes)
        matches = cls.filter(record_type, parent, **attributes)
        if matches:
            record = matches[0]
            print 'found match', record
            return record
        print 'match not found'


    @classmethod
    def _process_request(cls, record_type, request_func, parent=None, id=None, **request_args):
        path = cls._process_path(record_type, parent=parent, id=id)
        return request_func(path, **request_args)

    @classmethod
    def _process_filter_request(cls, record_type, parent=None, **filters):
        all_nones = not all(filters.values())
        if all_nones:
            raise cls.RecordError('at least one valid filter must be provided')
        params = { 'filter': filters }
        return cls._process_request(record_type, cls.connection.get, parent=parent, params=params)

    @classmethod
    def _process_path(cls, record_type, parent, id=None):
        if parent:
            return PathProcessor(record_type, parent_type=parent.record_type, parent_id=parent.id, id=id).path()
        else:
            return PathProcessor(record_type, id=id).path()

    @classmethod
    def _load_resources(cls, data):
        instances = []
        for item in data:
            instances.append(cls._load_resource(item))
        return instances

    @classmethod
    def _load_resource(cls, data):
        record_type = data['type']
        record_id = data['id']
        record_attributes = data['attributes']
        return cls(record_type, id=record_id, **record_attributes)

