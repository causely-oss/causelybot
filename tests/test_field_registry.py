"""
This class is used to test the FieldRegistry class in field_registry.py.
"""
from __future__ import annotations

import unittest

from causely_notification.field_registry import compute_impact_slo
from causely_notification.field_registry import FIELD_DEFINITIONS
from causely_notification.field_registry import FieldRegistry


class TestFieldRegistry(unittest.TestCase):
    def setUp(self):
        self.field_registry = FieldRegistry(FIELD_DEFINITIONS)

    def test_list_fields(self):
        fields = self.field_registry.list_fields()
        # Ensure all the defined fields are listed
        for field_name in FIELD_DEFINITIONS.keys():
            self.assertIn(field_name, fields)

    def test_get_direct_field_value(self):
        # Testing a direct field
        payload = {
            "severity": "high",
            "entity": {"type": "host"},
            "labels.k8s.cluster.name": "prod-cluster",
            "labels.k8s.namespace.name": "default",
            "name": "test-entity",
            "slos": {},
        }

        # Direct field test
        self.assertEqual(
            self.field_registry.get_field_value(payload, "severity"),
            "high",
        )
        self.assertEqual(
            self.field_registry.get_field_value(payload, "entity.type"),
            "host",
        )
        self.assertEqual(
            self.field_registry.get_field_value(
                payload, "labels.k8s.cluster.name",
            ),
            "prod-cluster",
        )

    def test_get_nested_direct_field_missing(self):
        # If a field path doesn't exist, it should return None
        payload = {
            "entity": {"type": "host"},
            "name": "test-entity",
        }
        self.assertIsNone(
            self.field_registry.get_field_value(
                payload, "labels.k8s.namespace.name",
            ),
        )

    def test_get_computed_field_value(self):
        # Testing a computed field
        payload = {
            "severity": "high",
            "entity": {"type": "host"},
            "slos": {"response_time": "OK"},
        }
        # 'impactsSLO' should return True since 'slos' is in the payload
        self.assertTrue(
            self.field_registry.get_field_value(payload, "impactsSLO"),
        )

        # If we remove 'slos', it should return False
        payload_no_slos = {
            "severity": "high",
            "entity": {"type": "host"},
        }
        self.assertFalse(
            self.field_registry.get_field_value(payload_no_slos, "impactsSLO"),
        )

    def test_register_field(self):
        # Test manual registration of a new field
        def dummy_extractor(payload):
            return "dummy_value"

        self.field_registry.register_field("custom.field", dummy_extractor)
        self.assertIn("custom.field", self.field_registry.list_fields())
        self.assertEqual(
            self.field_registry.get_field_value({}, "custom.field"),
            "dummy_value",
        )

    def test_get_field_value_nonexistent_field(self):
        with self.assertRaises(ValueError) as context:
            self.field_registry.get_field_value({}, "nonexistent.field")
        self.assertIn("is not registered", str(context.exception))

    def test_missing_computed_function(self):
        # If a computed field references a non-existing function
        broken_definitions = {
            "non_existent_func_field": {"type": "computed", "func": "some_missing_func"},
        }

        with self.assertRaises(ValueError) as context:
            FieldRegistry(broken_definitions)
        self.assertIn(
            "Function 'some_missing_func' for field 'non_existent_func_field' not found.",
            str(context.exception),
        )

    def test_direct_field_extractor_lambda(self):
        # Test the direct field extractor logic more explicitly
        payload = {
            "entity": {
                "type": "host",
                "attributes": {
                    "nested": "value",
                },
            },
        }
        # Register a new direct field to test the lambda extractor
        fr = FieldRegistry({})
        fr.register_field(
            "entity.attributes.nested",
            fr._create_extractor_for_path("entity.attributes.nested"),
        )
        self.assertEqual(
            fr.get_field_value(
                payload, "entity.attributes.nested",
            ), "value",
        )

    def test_compute_impact_slo_helper(self):
        # Test the helper function directly
        payload_with_slos = {"slos": {}}
        payload_without_slos = {}
        self.assertTrue(compute_impact_slo(payload_with_slos))
        self.assertFalse(compute_impact_slo(payload_without_slos))
