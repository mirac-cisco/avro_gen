from avrogen import avrojson
from avro import schema
import unittest
import six
import datetime

try:
    from avro.io import AvroTypeException
except ImportError:
    from avro.errors import AvroTypeException

make_avsc_object = schema.make_avsc_object


class AvroJsonTest(unittest.TestCase):
    converter = avrojson.AvroJsonConverter()
    converter_lt = avrojson.AvroJsonConverter(use_logical_types=True)

    def test_primitive_types(self):
        primitives = dict(int=1, float=2.0,
                          string='3.0', bytes=(b'foo', 'foo'), boolean=True, long=5, double=6.0, null=None)

        for t, v in six.iteritems(primitives):
            if isinstance(v, tuple):
                v, expected = v
            else:
                v, expected = v, v
            test_schema = schema.PrimitiveSchema(t)
            self.assertEqual(self.converter.to_json_object(v, test_schema), expected)
            self.assertEqual(self.converter.from_json_object(expected, test_schema), v)

    def test_enum(self):
        test_schema = schema.EnumSchema('test_enum', None, ['A', 'B'], schema.Names())
        self.assertEqual(self.converter.to_json_object('A', test_schema), 'A')
        self.assertEqual(self.converter.from_json_object('B', test_schema), 'B')

    def test_fixed(self):
        test_schema = schema.FixedSchema('test_enum', None, 5, schema.Names())
        self.assertEqual(self.converter.to_json_object(('A' * 5).encode('utf-8'), test_schema), ('A' * 5).encode('utf-8'))
        self.assertEqual(self.converter.from_json_object(('B' * 5).encode('utf-8'), test_schema), ('B' * 5).encode('utf-8'))

    def test_array(self):
        test_schema = make_avsc_object({'type': 'array', 'items': 'int'})
        self.assertEqual(self.converter.to_json_object([1, 2, 3], test_schema), [1, 2, 3])
        self.assertEqual(self.converter.from_json_object([1, 2, 3], test_schema), [1, 2, 3])

    def test_map(self):
        test_schema = make_avsc_object({'type': 'map', 'values': 'int'})
        d = dict(a=1, b=2, c=3)
        self.assertDictEqual(self.converter.to_json_object(d, test_schema), d)
        self.assertDictEqual(self.converter.from_json_object(d, test_schema), d)

    def test_union(self):
        test_schema = make_avsc_object(['null', 'int', 'string', {
            'type': 'record', 'name': 'test_record',
            'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'}
        ]}, {'type': 'record', 'name': 'test_record2', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'}
        ]}])
        result1 = dict(string='a')
        result2 = dict(int=2)

        self.assertIsNone(self.converter.to_json_object(None, test_schema))
        self.assertIsNone(self.converter.from_json_object(None, test_schema))

        self.assertDictEqual(self.converter.to_json_object('a', test_schema), result1)
        self.assertDictEqual(self.converter.to_json_object(2, test_schema), result2)

        self.assertEqual(self.converter.from_json_object(result1, test_schema), 'a')
        self.assertEqual(self.converter.from_json_object(result2, test_schema), 2)

    def test_record(self):
        test_schema = make_avsc_object({'type': 'record', 'name': 'test_record', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'}
        ]})

        d = dict(field1=2, field2='3')
        self.assertDictEqual(self.converter.to_json_object(d, test_schema), d)
        self.assertDictEqual(self.converter.from_json_object(d, test_schema), d)

    def test_schema_evolution(self):
        writers_schema = make_avsc_object({'type': 'record', 'name': 'test_record', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'}
        ]})

        readers_schema = make_avsc_object({'type': 'record', 'name': 'test_record', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'},
            {'name': 'field3', 'type': 'double', 'default': 3.0}
        ]})

        input = dict(field1=2, field2='3')
        output = dict(field1=2, field2='3', field3=3.0)

        self.assertDictEqual(self.converter.from_json_object(self.converter.to_json_object(input, writers_schema),
                                                             writers_schema, readers_schema),
                             output)

    def test_logical_type(self):
        writers_schema = make_avsc_object({'type': 'record', 'name': 'test_record', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'},
            {'name': 'date1', 'type': {'type': 'int', 'logicalType': 'date'}}
        ]})

        readers_schema = make_avsc_object({'type': 'record', 'name': 'test_record', 'fields': [
            {'name': 'field1', 'type': 'int'},
            {'name': 'field2', 'type': 'string'},
            {'name': 'field3', 'type': 'double', 'default': 3.0},
            {'name': 'date1', 'type': {'type': 'int', 'logicalType': 'date'}},
            {'name': 'date2', 'type': {'type': 'int', 'logicalType': 'date'}, 'default': 42}
        ]})

        input = dict(field1=2, field2='3', date1=datetime.date(2012, 3, 4))
        output1 = dict(field1=2, field2='3', date1=datetime.date(2012, 3, 4))
        output2 = dict(field1=2, field2='3', field3=3.0, date1=datetime.date(2012, 3, 4),
                       date2=datetime.date(1970, 2, 12))

        self.assertDictEqual(self.converter_lt.from_json_object(self.converter_lt.to_json_object(input, writers_schema),
                                                                writers_schema, writers_schema),
                             output1)
        self.assertDictEqual(self.converter_lt.from_json_object(self.converter_lt.to_json_object(input, writers_schema),
                                                                writers_schema, readers_schema),
                             output2)

    @unittest.expectedFailure
    def test_schema_mismatch(self):
        self.converter.from_json_object(42, make_avsc_object('int'), make_avsc_object('string'))

    def test_schema_discovery(self):
        from avrogen.dict_wrapper import DictWrapper

        class DD(DictWrapper):
            RECORD_SCHEMA = make_avsc_object(
                dict(type='record', name='record1', fields=[dict(name='f1', type='int')]))

            def __init__(self, f1: int):
                super().__init__()
                self._inner_dict['f1'] = f1

        self.assertDictEqual(self.converter.to_json_object(DD(f1=42)), dict(f1=42))

    def test_fail_logtype_validation_with_exc(self):
        schema = make_avsc_object({"type": "record", "name": "test_record", "fields": [
            {"name": "field1", "type": "int"},
            {"name": "field2", "type": "string"},
            {"name": "date1", "type": {"type": "int", "logicalType": "date"}}
        ]})

        input = dict(field1="1", field2="3", date1=11)

        with self.assertRaises(AvroTypeException):
            self.converter_lt.validate(schema, input, raise_on_error=True)

        self.assertFalse(self.converter_lt.validate(schema, input, raise_on_error=False))

    def test_fail_array_validation_with_exc(self):
        schema = make_avsc_object({"name":"test-array", "type": "array", "items": "int"})

        with self.assertRaises(AvroTypeException):
            self.converter.validate(schema, {"k1": "v1"}, raise_on_error=True)

        self.assertFalse(self.converter.validate(schema, input))

    def test_fail_map_validation_with_exc(self):
        schema = make_avsc_object({"type": "map", "values": "int"})
        with self.assertRaises(AvroTypeException):
            self.converter.validate(schema, [1,2,3], raise_on_error=True)

        # wrong dict key types
        with self.assertRaises(AvroTypeException):
            self.converter.validate(schema, {1: "hello", 2.33: "bye"},raise_on_error=True)

        # wrong value type
        with self.assertRaises(AvroTypeException):
            self.converter.validate(schema, {"k1": 22, "k3": "v3"}, raise_on_error=True)

    def test_fail_union_with_exc(self):
        test_schema = make_avsc_object({"name": "test", "type": "record",
            "fields": [
                {"name": "field1", "type": ["int", "string"]}
            ]})
        self.converter.validate(test_schema, {"field1": {"int": 22}}, raise_on_error=True)
        self.converter.validate(test_schema, {"field1": {"string": "22"}}, raise_on_error=True)

        with self.assertRaises(AvroTypeException):
            self.converter.validate(test_schema, {"field1": {"float": 22.2}}, raise_on_error=True)
        with self.assertRaises(AvroTypeException):
            self.converter.validate(test_schema, {"field1": None}, raise_on_error=True)

    def test_fail_record_with_exc(self):
        test_schema = make_avsc_object({"name": "test", "type": "record",
            "fields": [
                {"name": "field1", "type": "int"},
                {"name": "field2", "type": "string"}
            ]})

        with self.assertRaises(AvroTypeException):
            self.converter.validate(test_schema, ["not", "valid"], raise_on_error=True)

        with self.assertRaises(AvroTypeException):
            self.converter.validate(test_schema, {"field1": 22, "field2": 33}, raise_on_error=True)
