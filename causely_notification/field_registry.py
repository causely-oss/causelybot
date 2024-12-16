"""
This script defines field registry class which stores all the valid fields and how to access them in the payload.
"""
# TODO: Add more fields as needed
from __future__ import annotations
FIELD_DEFINITIONS = {
    "severity": {"type": "direct", "path": "severity"},
    "entity.type": {"type": "direct", "path": "entity.type"},
    "labels.k8s.cluster.name": {"type": "direct", "path": "labels.k8s.cluster.name"},
    "labels.k8s.namespace.name": {"type": "direct", "path": "labels.k8s.namespace.name"},
    "impactsSLO": {"type": "computed", "func": "compute_impact_slo"},
    "name": {"type": "direct", "path": "name"},
}


class FieldRegistry:
    """
    Manages field access and computation for nested and computed fields in a payload.
    """

    def __init__(self, field_definitions):
        self.registry = {}
        self.field_definitions = field_definitions
        self._register_fields()

    def _register_fields(self):
        """Automatically register all fields based on the field definitions."""
        for field_name, config in self.field_definitions.items():
            if config['type'] == 'direct':
                self.register_field(
                    field_name, self._create_extractor_for_path(
                        config['path'],
                    ),
                )
            elif config['type'] == 'computed':
                func = globals().get(config['func'])
                if func is None:
                    raise ValueError(f"Function '{config['func']}' for field '{
                                     field_name
                                     }' not found.")
                self.register_field(field_name, func)

    def register_field(self, field_name, extractor_func):
        """Register a field with an extraction function."""
        self.registry[field_name] = extractor_func

    def get_field_value(self, payload, field_name):
        """Retrieve the value of the field from the payload using the registered extractor."""
        if field_name not in self.registry:
            raise ValueError(f"Field '{field_name}' is not registered.")

        extractor_func = self.registry[field_name]
        return extractor_func(payload)

    def list_fields(self):
        """List all available registered fields."""
        return list(self.registry.keys())

    def _create_extractor_for_path(self, field_path):
        """Return an extractor function for a simple dot-notated field path."""
        return lambda payload: get_nested_value(payload, field_path.split('.'))


def get_nested_value(obj, path):
    """Get the value from a nested dictionary using dot notation."""
    full_key = '.'.join(path)
    if full_key in obj:
        return obj[full_key]

    for key in path:
        if key in obj:
            obj = obj[key]
        else:
            return None
    return obj


def compute_impact_slo(payload):
    """Compute if the SLO is impacted."""
    return "slos" in payload
