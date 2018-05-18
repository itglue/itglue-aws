import requests
import json
import os

class Connection:
    def __init__(self):
        self.api_key = os.environ['ITGLUE_API_KEY']
        self.host = os.environ['ITGLUE_API_URL']
        self.default_headers = {
            'Content-Type': 'application/vnd.api+json',
            'x-api-key': self.api_key
        }

    def get(self, path, params=None):
        url = self._url_for(path)
        response = self._process_request(requests.get, url, params=params)
        print(response.url)
        return self._process_response(response)

    def post(self, path, payload=None, relationships=None):
        data = self.process_payload(payload, relationships)
        url = self._url_for(path)
        response = self._process_request(requests.post, url, data=data)
        return self._process_response(response)

    def patch(self, path, payload=None):
        data = self.process_payload(payload)
        url = self._url_for(path)
        response = self._process_request(requests.patch, url, data=data)
        return self._process_response(response)

    def _process_response(self, response):
        parsed_response = response.json()
        data = parsed_response['data']
        if type(data) is not list:
            return data
        meta = parsed_response.get('meta', {})
        links = parsed_response.get('links', {})
        while meta.get('next-page') and links.get('next'):
            url = links['next']
            next_resp = self._process_request(requests.get, url)
            next_parsed_resp = next_resp.json()
            data.extend(next_parsed_resp['data'])
            meta = next_parsed_resp.get('meta', {})
            links = next_parsed_resp.get('links', {})
        return data


    def _process_request(self, request_func, url, data=None, params=None):
        url_formatted_params = self._format_params(params) if params else None
        response = request_func(url, headers=self.default_headers, data=data, params=url_formatted_params)
        response.raise_for_status()
        return response

    def _format_params(self, params, namespace=None):
        params_list = []
        for key, value in params.iteritems():
            if value:
                namespace = '{}[{}]'.format(namespace, key) if namespace else key
                if type(value) is dict:
                    params_list.append(self._format_params(value, namespace=namespace))
                elif type(value) is list:
                    formatted_list = ','.join(map(str, value))
                    params_list.append("{}={}".format(namespace, formatted_list))
                else:
                    params_list.append("{}={}".format(namespace, value))
        return '&'.join(params_list)

    def _url_for(self, path):
        return '{}{}'.format(self.host, path)

    def process_payload(self, payload, relationships=None):
        if payload:
            if relationships:
                payload['relationships'] = {}
                for rel_name, rel_items in relationships.iteritems():
                    payload['relationships'][rel_name] = self.data_wrap(rel_items)
            return json.dumps(self.data_wrap(payload))

    @staticmethod
    def data_wrap(payload):
        return { 'data': payload }

