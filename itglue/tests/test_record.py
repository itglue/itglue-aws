import unittest
from unittest.mock import patch, MagicMock, create_autospec

from .. import itglue

class TestData(object):
    record_type = 'configurations'
    record_id = 123
    record_name = 'ITG-MBP15-13'
    record_alt_name = 'ITG-MBP15-21'
    record_notes = 'Some notes'
    record_ip = '123.456.789.10'
    parent_type = 'organizations'
    parent_name = 'Happy Frog'
    record_class = itglue.Record
    data_dict = {
        'id': record_id,
        'type': record_type,
        'attributes': {'name': record_alt_name}
    }
    data_list = [
        {
            'id': record_id,
            'type': record_type,
            'attributes': {'name': record_alt_name}
        }
    ]
    record_from_data = itglue.Record(
        record_type,
        id=record_id,
        name=record_alt_name
    )

class TestRecord(unittest.TestCase):
    """Basic test cases."""

    def setUp(self):
        self.mock_connection = MagicMock()
        patcher = patch('itglue.itglue.record.connection', self.mock_connection)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.record_class = itglue.Record
        self.parent_record = itglue.Record(TestData.parent_type, name=TestData.parent_name)
        self.record = itglue.Record(
            TestData.record_type,
            name=TestData.record_name,
            notes=TestData.record_notes
        )

    def tearDown(self):
        self.parent_record = None
        self.record = None

    def test_record_type(self):
        self.assertEqual(self.record.record_type, TestData.record_type)

    def test_id(self):
        self.record.id = TestData.record_id
        self.assertEqual(self.record.id, TestData.record_id)

    def test_attributes(self):
        self.assertEqual(self.record.attributes, {'name': TestData.record_name, 'notes': TestData.record_notes})

    def test_get_attr(self):
        self.assertEqual(self.record.get_attr('name'), TestData.record_name)
        self.assertEqual(self.record.get_attr('notes'), TestData.record_notes)
        self.assertEqual(self.record.get_attr('foo'), None)

    def test_set_attr(self):
        self.assertEqual(self.record.set_attr('primary_ip', TestData.record_ip), TestData.record_ip)
        self.assertEqual(self.record.attributes['primary_ip'], TestData.record_ip)
        self.assertEqual(self.record.get_attr('primary_ip'), TestData.record_ip)

    def test_set_attributes(self):
        self.record.set_attributes(name=TestData.record_alt_name, primary_ip=TestData.record_ip)
        self.assertEqual(self.record.attributes['name'], TestData.record_alt_name)
        self.assertEqual(self.record.attributes['primary_ip'], TestData.record_ip)

    def test_save_new(self):
        with patch.object(itglue.record.connection, 'post', return_value=TestData.data_dict):
            expected_path = '/{}'.format(TestData.record_type)
            expected_payload = {
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.save(), TestData.record_from_data)
            self.mock_connection.post.assert_called_once_with(expected_path, payload=expected_payload, relationships={})

    def test_save_existing(self):
        with patch.object(itglue.record.connection, 'patch', return_value=TestData.data_dict):
            self.record.id = TestData.record_id
            self.record.set_attr('name', TestData.record_alt_name)
            expected_path = '/{}/{}'.format(TestData.record_type, TestData.record_id)
            expected_payload = {
                'id': TestData.record_id,
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_alt_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.save(), TestData.record_from_data)
            self.mock_connection.patch.assert_called_once_with(expected_path, payload=expected_payload)

    def test_save_with_parent(self):
        with patch.object(itglue.record.connection, 'post', return_value=TestData.data_dict):
            self.parent_record.id = 456
            expected_path = '/{parent_type}/{parent_id}/relationships/{record_type}'.format(
                parent_type=self.parent_record.record_type,
                parent_id=self.parent_record.id,
                record_type=TestData.record_type
            )
            expected_payload = {
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.save(parent=self.parent_record), TestData.record_from_data)
            self.mock_connection.post.assert_called_once_with(expected_path, payload=expected_payload, relationships={})

    def test_create_error(self):
        self.record.id = TestData.record_id
        self.assertRaises(itglue.Record.RecordError, self.record.create)

    def test_create_success(self):
        with patch.object(itglue.record.connection, 'post', return_value=TestData.data_dict):
            expected_path = '/{}'.format(TestData.record_type)
            expected_payload = {
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.create(), TestData.record_from_data)
            self.mock_connection.post.assert_called_once_with(expected_path, payload=expected_payload, relationships={})

    def test_create_with_relationships(self):
        with patch.object(itglue.record.connection, 'post', return_value=TestData.data_dict):
            interface_1 = itglue.Record('configuration_interface', name='eni-545f123a', ip_address='1.2.3.4')
            interface_2 = itglue.Record('configuration_interface', name='eni-545f789a', ip_address='5.6.7.8')

            expected_path = '/{}'.format(TestData.record_type)
            expected_payload = {
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name,
                    'notes': TestData.record_notes
                }
            }
            expected_rel_payload = {
                'configuration_interfaces': [
                    {
                        'type': 'configuration_interface',
                        'attributes': {'name': 'eni-545f123a', 'ip_address': '1.2.3.4'}
                    },
                    {
                        'type': 'configuration_interface',
                        'attributes': {'name': 'eni-545f789a', 'ip_address': '5.6.7.8'}
                    }
                ]
            }
            record = self.record.create(configuration_interfaces=[interface_1, interface_2])
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.post.assert_called_once_with(
                expected_path,
                payload=expected_payload,
                relationships=expected_rel_payload
            )

    def test_update_error(self):
        self.assertRaises(itglue.Record.RecordError, self.record.update)

    def test_update_success(self):
        with patch.object(itglue.record.connection, 'patch', return_value=TestData.data_dict):
            self.record.id = TestData.record_id
            self.record.set_attr('name', TestData.record_alt_name)
            expected_path = '/{}/{}'.format(TestData.record_type, TestData.record_id)
            expected_payload = {
                'id': TestData.record_id,
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_alt_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.update(), TestData.record_from_data)
            self.mock_connection.patch.assert_called_once_with(expected_path, payload=expected_payload)

    def test_update_with_parent(self):
        with patch.object(itglue.record.connection, 'patch', return_value=TestData.data_dict):
            self.parent_record.id = 456
            self.record.id = TestData.record_id
            expected_path = '/{parent_type}/{parent_id}/relationships/{record_type}/{record_id}'.format(
                parent_type=self.parent_record.record_type,
                parent_id=self.parent_record.id,
                record_type=TestData.record_type,
                record_id=TestData.record_id
            )
            expected_payload = {
                'id': TestData.record_id,
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name,
                    'notes': TestData.record_notes
                }
            }
            self.assertEqual(self.record.update(parent=self.parent_record), TestData.record_from_data)
            self.mock_connection.patch.assert_called_once_with(expected_path, payload=expected_payload)

    def test_update_with_parent_error(self):
        self.parent_record.id = None
        self.record.id = TestData.record_id
        with self.assertRaises(itglue.Record.RecordError):
            self.record.update(parent=self.parent_record)


    def test_reload(self):
        self.assertEqual(self.record._reload(TestData.data_dict), self.record)
        self.assertEqual(self.record.id, TestData.record_id)
        self.assertEqual(self.record.record_type, TestData.record_type)
        self.assertEqual(self.record.get_attr('name'), TestData.record_alt_name)

    def test_payload(self):
        self.record.id = TestData.record_id
        expected_payload = {
            'id': TestData.record_id,
            'type': TestData.record_type,
            'attributes': {
                'name': TestData.record_name,
                'notes': TestData.record_notes
            }
        }
        self.assertEqual(self.record.payload(), expected_payload)

    def test_relationships_payload(self):
        interface_1 = itglue.Record('configuration_interface', name='eni-545f123a', ip_address='1.2.3.4')
        interface_2 = itglue.Record('configuration_interface', name='eni-545f789a', ip_address='5.6.7.8')
        expected_rel_payload = {
            'configuration_interfaces': [
                {
                    'type': 'configuration_interface',
                    'attributes': {'name': 'eni-545f123a', 'ip_address': '1.2.3.4'}
                },
                {
                    'type': 'configuration_interface',
                    'attributes': {'name': 'eni-545f789a', 'ip_address': '5.6.7.8'}
                }
            ]
        }
        rel_payload = self.record_class._relationships_payload({'configuration_interfaces': [interface_1, interface_2]})
        self.assertEqual(rel_payload, expected_rel_payload)

    def test_get(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            expected_path = '/{}'.format(TestData.record_type)
            self.assertEqual(self.record_class.get(TestData.record_type), [TestData.record_from_data])
            self.mock_connection.get.assert_called_once_with(expected_path)

    def test_get_with_parent(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            self.parent_record.id = 456
            expected_path = '/{parent_type}/{parent_id}/relationships/{record_type}'.format(
                parent_type=self.parent_record.record_type,
                parent_id=self.parent_record.id,
                record_type=TestData.record_type
            )
            records = self.record_class.get(TestData.record_type, parent=self.parent_record)
            self.assertEqual(records, [TestData.record_from_data])
            self.mock_connection.get.assert_called_once_with(expected_path)

    def test_filter(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            records = self.record_class.filter(TestData.record_type, name=TestData.record_name)
            self.assertEqual(records, [TestData.record_from_data])
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)

    def test_filter_no_filter_error(self):
        with self.assertRaises(itglue.Record.RecordError):
            self.record_class.filter(TestData.record_type)

    def test_filter_all_nones_error(self):
        with self.assertRaises(itglue.Record.RecordError):
            self.record_class.filter(TestData.record_type, name=None, notes='')

    def test_find(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_dict):
            expected_path = '/{}/{}'.format(TestData.record_type, TestData.record_id)
            record = self.record_class.find(TestData.record_type, TestData.record_id)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path)

    def test_find_with_parent(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_dict):
            self.parent_record.id = 456
            expected_path = '/{parent_type}/{parent_id}/relationships/{record_type}/{record_id}'.format(
                parent_type=self.parent_record.record_type,
                parent_id=self.parent_record.id,
                record_type=TestData.record_type,
                record_id=TestData.record_id
            )
            record = self.record_class.find(TestData.record_type, TestData.record_id, parent=self.parent_record)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path)

    def test_first_or_create_with_match(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            record = self.record_class.first_or_create(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)
            self.mock_connection.post.assert_not_called()

    def test_first_or_create_without_match(self):
        with patch.object(itglue.record.connection, 'get', return_value=[]), \
                patch.object(itglue.record.connection, 'post', return_value=TestData.data_dict):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            expected_payload = {
                'type': TestData.record_type,
                'attributes': {
                    'name': TestData.record_name
                }
            }
            record = self.record_class.first_or_create(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)
            self.mock_connection.post.assert_called_once_with(expected_path, payload=expected_payload, relationships={})

    def test_first_or_initialize_with_match(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            record = self.record_class.first_or_initialize(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)
            self.mock_connection.post.assert_not_called()

    def test_first_or_initialize_without_match(self):
        with patch.object(itglue.record.connection, 'get', return_value=[]):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            record = self.record_class.first_or_initialize(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, itglue.Record(TestData.record_type, name=TestData.record_name))
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)
            self.mock_connection.post.assert_not_called()

    def test_find_by(self):
        with patch.object(itglue.record.connection, 'get', return_value=TestData.data_list):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            record = self.record_class.find_by(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, TestData.record_from_data)
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)

    def test_find_by_no_matches(self):
        with patch.object(itglue.record.connection, 'get', return_value=[]):
            expected_path = '/{}'.format(TestData.record_type)
            expected_params = { 'filter': { 'name': TestData.record_name } }
            record = self.record_class.find_by(TestData.record_type, name=TestData.record_name)
            self.assertEqual(record, None)
            self.mock_connection.get.assert_called_once_with(expected_path, params=expected_params)

    def test_find_by_no_attributes_error(self):
        with self.assertRaises(itglue.Record.RecordError):
            self.record_class.find_by(TestData.record_type)

    def test_find_by_all_empty_error(self):
        with self.assertRaises(itglue.Record.RecordError):
            self.record_class.find_by(TestData.record_type, name=None, notes='')

if __name__ == '__main__':
    unittest.main()
