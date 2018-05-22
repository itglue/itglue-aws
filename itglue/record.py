from connection import connection
from path_processor import PathProcessor

class Record(object):
    class RecordError(Exception):
        pass

    def __init__(self, record_type, id=None, **attributes):
        self.record_type = record_type
        self.attributes = attributes
        self.id = id

    def __repr__(self):
        return "<{class_name} type: {type}, id: {id}, attributes: {attributes}>".format(
            class_name=self.__class__.__name__,
            type=self.record_type,
            id=self.id,
            attributes=self.attributes
        )

    def get_attr(self, attr_name):
        """
        Get the value of an attribute.
        :param attr_name str: the name of the attribute being fetched
        :returns: the attribute value or None if it is not set
        """
        return self.attributes.get(attr_name)

    def set_attr(self, attr_name, attr_value):
        """
        Set the value of an attribute.
        :param attr_name str: the name of the attribute being set
        :param attr_value: the value of the attribute being set
        :returns: the attribute value
        """
        self.attributes[attr_name] = attr_value
        return attr_value

    def set_attributes(self, **attributes_dict):
        """
        Set the value of multiple attributes.
        :param attributes_dict dict: a dictionary containing key-value pairs as attribute names and values to be set
        :returns: the record itself
        """
        for attr_name, attr_value in attributes_dict.iteritems():
            self.set_attr(attr_name, attr_value)
        return self

    def save(self):
        """
        Either creates a record or updates it (if it already has an id).
        This will trigger an api POST or PATCH request.
        :returns: the record itself
        """
        if self.id:
            return self.update()
        else:
            return self.create()

    def create(self, parent=None, **relationships):
        """
        Creates the record. This will trigger an api POST request.
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param **relationships: any number of lists as keyword arguments to be submitted as relationships
            for the request, e.g. relationship_name=[record1, record2]
        :raises RecordError: if the record has an id (already exists)
        :returns: the record itself
        """
        if self.id:
            raise self.RecordError('cannot create a record with an existing ID')
        data = self.__class__._process_request(
            self.record_type,
            connection.post,
            parent=parent,
            payload=self.payload(),
            relationships=self._relationships_payload(relationships)
        )
        return self._reload(data)

    def update(self, parent=None):
        """
        Updates the record. This will trigger an api PATCH request.
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :raises RecordError: if the record does not have an id (does not exist yet)
        :returns: the record itself
        """
        if not self.id:
            raise self.RecordError('cannot update a record without an ID')
        data = self.__class__._process_request(
            self.record_type,
            connection.patch,
            parent=parent,
            id=self.id,
            payload=self.payload()
        )
        return self._reload(data)

    def _reload(self, data):
        # Loads the id, attributes and record_type properties based on a data dict
        self.id = data['id']
        self.attributes = data['attributes']
        self.record_type = data['type']
        return self

    def payload(self):
        """
        Renders the record payload.
        :returns: a dict representing the object to be used as payload for a request
        """
        payload = {'type': self.record_type, 'attributes': self.attributes }
        if self.id:
            payload['id'] = self.id
        return payload

    @staticmethod
    def _relationships_payload(relationships):
        # Returns a dict representing the relationships, used as a payload for a request
        rel_payload = {}
        for rel_name, rel_items in relationships.iteritems():
            rel_payload[rel_name] = list(map(lambda rel_item: rel_item.payload(), rel_items))
        return rel_payload

    @classmethod
    def get(cls, record_type, parent=None):
        """
        Gets all records of the given type and parent (if provided). This will trigger an api GET request.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :returns: a list of matching records
        """
        data = cls._process_request(record_type, connection.get, parent=parent)
        return cls._load_resources(data)

    @classmethod
    def filter(cls, record_type, parent=None, **filters):
        """
        Gets all records of the given type and parent (if provided) which match the given filters.
        This will trigger an api GET request.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param **filters: any number of keyword arguments to filter by, e.g name='example name'
        :returns: a list of matching records
        """
        data = cls._process_filter_request(record_type, parent, **filters)
        return cls._load_resources(data)

    @classmethod
    def find(cls, record_type, id, parent=None):
        """
        Gets the record of the given type and parent (if provided) with matching id.
        This will trigger an api GET request.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param id int: the id of the record to be fetched
        :returns: the matching record
        :raises RecordError: if the record cannot be found
        """
        try:
            data = cls._process_request(record_type, connection.get, parent=parent, id=id)
            return cls._load_resource(data)
        except connection.RequestError as error:
            raise cls.RecordError(error)

    @classmethod
    def first_or_create(cls, record_type, parent=None, **attributes):
        """
        Attempts to find the first record with the same attributes, creates the record if no matches are found.
        This will trigger an api GET request and a POST request if the record does not exist.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search/create the record
        :returns: a record instance - the existing one if found, otherwise the newly created one
        """
        existing_record = cls.find_by(record_type, parent, **attributes)
        if existing_record:
            return existing_record
        return cls(record_type, **attributes).create()

    @classmethod
    def first_or_initialize(cls, record_type, parent=None, **attributes):
        """
        Attempts to find the first record with the same attributes, initialized the record if no matches are found.
        This will trigger an api GET request.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search/initialize the record
        :returns: a record instance - the existing one if found, otherwise the newly instantiated one
        """
        existing_record = cls.find_by(record_type, parent, **attributes)
        if existing_record:
            return existing_record
        return cls(record_type, **attributes)

    @classmethod
    def find_by(cls, record_type, parent=None, **attributes):
        """
        Gets the first record of the given type and parent (if provided) with matching attributes.
        This will trigger an api GET request.
        :param record_type str: the type of the record
        :param parent Record: the parent of the record - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search the record by
        :returns: the matching record, None if not found
        """
        if not attributes:
            raise cls.RecordError('at least one attribute must be provided')
        matches = cls.filter(record_type, parent, **attributes)
        if matches:
            return matches[0]

    @classmethod
    def _process_request(cls, record_type, request_func, parent=None, id=None, **request_args):
        # Processes the request by processing the path and executing the request_func with request_args
        path = cls._process_path(record_type, parent=parent, id=id)
        return request_func(path, **request_args)

    @classmethod
    def _process_filter_request(cls, record_type, parent=None, **filters):
        # Processes a filter get request ensuring the request arguments are formatted properly
        all_nones = not all(filters.values())
        if all_nones:
            raise cls.RecordError('at least one valid filter must be provided')
        params = { 'filter': filters }
        return cls._process_request(record_type, connection.get, parent=parent, params=params)

    @classmethod
    def _process_path(cls, record_type, parent, id=None):
        # Delegates path processing to PathProcessor, ensuring the correct arguments are provided
        if parent:
            return PathProcessor(record_type, parent_type=parent.record_type, parent_id=parent.id, id=id).path()
        else:
            return PathProcessor(record_type, id=id).path()

    @classmethod
    def _load_resources(cls, data):
        # Loads a number of resources by instantiating them with the given data list
        instances = []
        for item in data:
            instances.append(cls._load_resource(item))
        return instances

    @classmethod
    def _load_resource(cls, data):
        # Loads one resource by instantiating it witha given data dict
        record_type = data['type']
        record_id = data['id']
        record_attributes = data['attributes']
        return cls(record_type, id=record_id, **record_attributes)
