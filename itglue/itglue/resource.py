from . import connection
from . import process_path

class Resource(object):
    class ResourceError(Exception):
        pass

    def __init__(self, resource_type, id=None, **attributes):
        self.resource_type = resource_type
        self.attributes = attributes
        self.id = id

    def __repr__(self):
        return "<{class_name} type: {type}, id: {id}, attributes: {attributes}>".format(
            class_name=self.__class__.__name__,
            type=self.resource_type,
            id=self.id,
            attributes=self.attributes
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.resource_type == other.resource_type and self.id == other.id and self.attributes == other.attributes
        return False

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
        :returns: the resource itself
        """
        for attr_name, attr_value in attributes_dict.items():
            self.set_attr(attr_name, attr_value)
        return self

    def save(self, parent=None):
        """
        Either creates a resource or updates it (if it already has an id).
        This will trigger an api POST or PATCH request.
        :returns: the resource itself
        """
        if self.id:
            return self.update(parent=parent)
        else:
            return self.create(parent=parent)

    def create(self, parent=None, **relationships):
        """
        Creates the resource. This will trigger an api POST request.
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param **relationships: any number of lists as keyword arguments to be submitted as relationships
            for the request, e.g. relationship_name=[resource1, resource2]
        :raises ResourceError: if the resource has an id (already exists)
        :returns: the resource itself
        """
        if self.id:
            raise self.ResourceError('cannot create a resource with an existing ID')
        data = self.__class__._process_request(
            self.resource_type,
            connection.post,
            parent=parent,
            payload=self.payload(),
            relationships=self._relationships_payload(relationships)
        )
        return self._reload(data)

    def update(self, parent=None):
        """
        Updates the resource. This will trigger an api PATCH request.
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :raises ResourceError: if the resource does not have an id (does not exist yet)
        :returns: the resource itself
        """
        if not self.id:
            raise self.ResourceError('cannot update a resource without an ID')
        data = self.__class__._process_request(
            self.resource_type,
            connection.patch,
            parent=parent,
            id=self.id,
            payload=self.payload()
        )
        return self._reload(data)

    def _reload(self, data):
        # Loads the id, attributes and resource_type properties based on a data dict
        self.id = data['id']
        self.attributes = data['attributes']
        self.resource_type = data['type']
        return self

    def payload(self):
        """
        Renders the resource payload.
        :returns: a dict representing the object to be used as payload for a request
        """
        payload = {'type': self.resource_type, 'attributes': self.attributes }
        if self.id:
            payload['id'] = self.id
        return payload

    @staticmethod
    def _relationships_payload(relationships):
        # Returns a dict representing the relationships, used as a payload for a request
        rel_payload = {}
        for rel_name, rel_items in relationships.items():
            rel_payload[rel_name] = list(map(lambda rel_item: rel_item.payload(), rel_items))
        return rel_payload

    @classmethod
    def get(cls, resource_type, parent=None):
        """
        Gets all resources of the given type and parent (if provided). This will trigger an api GET request.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :returns: a list of matching resources
        """
        data = cls._process_request(resource_type, connection.get, parent=parent)
        return cls._load_resources(data)

    @classmethod
    def filter(cls, resource_type, parent=None, **filters):
        """
        Gets all resources of the given type and parent (if provided) which match the given filters.
        This will trigger an api GET request.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param **filters: any number of keyword arguments to filter by, e.g name='example name'
        :returns: a list of matching resources
        """
        data = cls._process_filter_request(resource_type, parent, **filters)
        return cls._load_resources(data)

    @classmethod
    def find(cls, resource_type, id, parent=None):
        """
        Gets the resource of the given type and parent (if provided) with matching id.
        This will trigger an api GET request.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param id int: the id of the resource to be fetched
        :returns: the matching resource
        :raises ResourceError: if the resource cannot be found
        """
        try:
            data = cls._process_request(resource_type, connection.get, parent=parent, id=id)
            return cls._load_resource(data)
        except connection.RequestError as error:
            raise cls.ResourceError(error)

    @classmethod
    def first_or_create(cls, resource_type, parent=None, **attributes):
        """
        Attempts to find the first resource with the same attributes, creates the resource if no matches are found.
        This will trigger an api GET request and a POST request if the resource does not exist.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search/create the resource
        :returns: a resource instance - the existing one if found, otherwise the newly created one
        """
        existing_resource = cls.find_by(resource_type, parent, **attributes)
        if existing_resource:
            return existing_resource
        return cls(resource_type, **attributes).create()

    @classmethod
    def first_or_initialize(cls, resource_type, parent=None, **attributes):
        """
        Attempts to find the first resource with the same attributes, initialized the resource if no matches are found.
        This will trigger an api GET request.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search/initialize the resource
        :returns: a resource instance - the existing one if found, otherwise the newly instantiated one
        """
        existing_resource = cls.find_by(resource_type, parent, **attributes)
        if existing_resource:
            return existing_resource
        return cls(resource_type, **attributes)

    @classmethod
    def find_by(cls, resource_type, parent=None, **attributes):
        """
        Gets the first resource of the given type and parent (if provided) with matching attributes.
        This will trigger an api GET request.
        :param resource_type str: the type of the resource
        :param parent Resource: the parent of the resource - used for nesting the request url, optional
        :param **attributes: any number of keyword arguments as attributes to search the resource by
        :returns: the matching resource, None if not found
        :raises ResourceError: if the no valid attributes are provided
        """
        all_nones = not all(attributes.values())
        if not attributes or all_nones:
            raise cls.ResourceError('at least one attribute must be provided')
        matches = cls.filter(resource_type, parent, **attributes)
        if matches:
            return matches[0]

    @classmethod
    def _process_request(cls, resource_type, request_func, parent=None, id=None, **request_args):
        # Processes the request by processing the path and executing the request_func with request_args
        path = cls._process_path(resource_type, parent=parent, id=id)
        return request_func(path, **request_args)

    @classmethod
    def _process_filter_request(cls, resource_type, parent=None, **filters):
        # Processes a filter get request ensuring the request arguments are formatted properly
        all_nones = not all(filters.values())
        if not filters or all_nones:
            raise cls.ResourceError('at least one valid filter must be provided')
        params = { 'filter': filters }
        return cls._process_request(resource_type, connection.get, parent=parent, params=params)

    @classmethod
    def _process_path(cls, resource_type, parent, id=None):
        # Delegates path processing to path_processor.process_path, ensuring the correct arguments are provided
        if parent:
            if not parent.resource_type:
                raise cls.ResourceError('provided parent does not have a resource_type')
            elif not parent.id:
                raise cls.ResourceError('provided parent does not have an id')
            else:
                return process_path(resource_type, parent_type=parent.resource_type, parent_id=parent.id, id=id)
        else:
            return process_path(resource_type, id=id)

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
        resource_type = data['type']
        resource_id = data['id']
        resource_attributes = data['attributes']
        return cls(resource_type, id=resource_id, **resource_attributes)
