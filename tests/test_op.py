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
This class adds unit tests for the Operator class in op.py.
"""
from __future__ import annotations

import unittest

from causely_notification.op import Operator


class TestOperator(unittest.TestCase):
    def test_init_with_valid_operator(self):
        # Test that initializing with a valid operator doesn't raise an error
        op = Operator("equals")
        self.assertEqual(op.operator, "equals")

    def test_init_with_invalid_operator(self):
        # Test that initializing with an invalid operator raises ValueError
        with self.assertRaises(ValueError) as context:
            Operator("some_invalid_op")
        self.assertIn("Invalid operator", str(context.exception))

    def test_apply_equals_operator(self):
        # Test equals operator
        op = Operator("equals")
        self.assertTrue(op.apply(5, 5))
        self.assertFalse(op.apply(5, 6))

    def test_apply_not_equals_operator(self):
        # Test not_equals operator
        op = Operator("not_equals")
        self.assertTrue(op.apply(5, 6))
        self.assertFalse(op.apply(5, 5))

    def test_apply_in_operator_with_list(self):
        # Test in operator with a valid list value
        op = Operator("in")
        self.assertTrue(op.apply("apple", ["apple", "banana"]))
        self.assertFalse(op.apply("cherry", ["apple", "banana"]))

    def test_apply_in_operator_with_invalid_type(self):
        # Test in operator with an invalid value type
        op = Operator("in")
        with self.assertRaises(ValueError) as context:
            op.apply("apple", "not a list")
        self.assertIn("Operator 'in' requires a list", str(context.exception))

    def test_apply_not_in_operator_with_list(self):
        # Test not_in operator with a valid list value
        op = Operator("not_in")
        self.assertTrue(op.apply("cherry", ["apple", "banana"]))
        self.assertFalse(op.apply("apple", ["apple", "banana"]))

    def test_apply_not_in_operator_with_invalid_type(self):
        # Test not_in operator with an invalid value type
        op = Operator("not_in")
        with self.assertRaises(ValueError) as context:
            op.apply("apple", "not a list")
        self.assertIn(
            "Operator 'not_in' requires a list",
            str(context.exception),
        )
