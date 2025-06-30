# Copyright 2025 Causely, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
This class defines an operator class where valid operators are registered and used to evaluate apply the operator on the runtime data in
comparison to the filter data.
"""
from __future__ import annotations


class Operator:
    def __init__(self, operator):
        self.operator = operator
        self.valid_operators = [
            'equals', 'not_equals',
            'in', 'not_in',
        ]
        if operator not in self.valid_operators:
            raise ValueError(f"Invalid operator '{operator}'. Valid operators are {
                             self.valid_operators
                             }")

    def apply(self, field_value, value):
        """Apply the operator to the given field_value and target value."""
        method_name = f"_apply_{self.operator}"
        method = getattr(self, method_name, None)
        if not method:
            raise NotImplementedError(
                f"Operator '{self.operator}' not implemented.",
            )
        return method(field_value, value)

    def _apply_equals(self, field_value, value):
        return field_value == value

    def _apply_in(self, field_value, value):
        if not isinstance(value, list):
            raise ValueError(
                f"Operator 'in' requires a list as value, but got {
                    type(value)
                }",
            )
        return field_value in value

    def _apply_not_equals(self, field_value, value):
        return field_value != value

    def _apply_not_in(self, field_value, value):
        if not isinstance(value, list):
            raise ValueError(
                f"Operator 'not_in' requires a list as value, but got {
                    type(value)
                }",
            )
        return field_value not in value
