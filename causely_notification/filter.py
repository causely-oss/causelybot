"""
This class defines filtering mechanism to match a payload with a filter configuration. If it does then it forwards the payload to that particular slack channel.
Otherwise, it does not forward the payload to any slack channel.
"""
from __future__ import annotations

import bitarray
import mmh3

from causely_notification.field_registry import FIELD_DEFINITIONS
from causely_notification.field_registry import FieldRegistry
from causely_notification.op import Operator


class WebhookFilterStore:
    """
    Stores filters for each webhook.
    Uses Bloom filters to quickly check if a payload matches any webhook's filters.
    """

    def __init__(self):
        self.webhook_filters = {}
        self.field_registry = FieldRegistry(FIELD_DEFINITIONS)

    def add_webhook_filters(self, webhook_name, filters, enabled=False):
        """Add filters for a specific webhook."""
        if webhook_name not in self.webhook_filters:
            self.webhook_filters[webhook_name] = FilterIndex(
                self.field_registry, enabled,
            )

        for filter_ in filters:
            field = filter_['field']
            operator = filter_['operator']
            value = filter_['value']
            self.webhook_filters[webhook_name].add_filter(
                field, operator, value,
            )

    def filter_payload(self, payload):
        """Filter the payload against all webhooks and return matching webhooks."""
        matching_webhooks = []
        for webhook_name, filter_index in self.webhook_filters.items():
            # If the filter index is not enabled, then this is a match webhook as it allows all payloads by default
            if not filter_index.enabled:
                matching_webhooks.append(webhook_name)
                continue
            # If we get here, then we need to check the payload against the filters
            if filter_index.check_payload(payload):
                matching_webhooks.append(webhook_name)
        return matching_webhooks


class FilterIndex:
    """
    Represents a collection of filters for a specific webhook.
    Uses Bloom filters to store membership-based filters
    and Operator class for numeric or string comparison operators.
    """

    def __init__(self, field_registry, enabled):
        self.field_filters = {}
        self.field_registry = field_registry
        self.enabled = enabled

    def add_filter(self, field, operator, value):
        """Add a filter for a specific field."""
        if field not in self.field_filters:
            self.field_filters[field] = {
                'bloom': None,
                'operator': [],
            }

        # Use Bloom filters for 'in' and 'equals'
        if operator in ['equals', 'in']:
            if self.field_filters[field]['bloom'] is None:
                self.field_filters[field]['bloom'] = BloomFilter(
                    size=1000, num_hashes=3,
                )

            if isinstance(value, list):
                for val in value:
                    self.field_filters[field]['bloom'].add(str(val))
            else:
                self.field_filters[field]['bloom'].add(str(value))
        else:
            # For greater_than, less_than, and other complex operators
            self.field_filters[field]['operator'].append({
                'operator': operator,
                'value': value,
            })

    def check_payload(self, payload):
        """Check if the payload matches all filters for this webhook."""
        for field, filters in self.field_filters.items():
            field_value = self.field_registry.get_field_value(payload, field)

            # If the field value is None, the filter does not match
            if field_value is None:
                return False

            # Check membership-based conditions using Bloom filter
            if filters['bloom'] is not None and field_value is not None:
                if not filters['bloom'].check(str(field_value)):
                    return False

            # Check non-membership conditions using the Operator class
            for op in filters['operator']:
                operator_instance = Operator(op['operator'])
                if not operator_instance.apply(field_value, op['value']):
                    return False

        return True


class BloomFilter:
    """Simple implementation of a Bloom filter."""

    def __init__(self, size, num_hashes):
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array = bitarray.bitarray(size)
        self.bit_array.setall(0)

    def _hashes(self, item):
        for i in range(self.num_hashes):
            yield mmh3.hash(item, i) % self.size

    def add(self, item):
        for hash_value in self._hashes(item):
            self.bit_array[hash_value] = 1

    def check(self, item):
        return all(self.bit_array[hash_value] for hash_value in self._hashes(item))
