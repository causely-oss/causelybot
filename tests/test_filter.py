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
This class is used to test the FilterIndex, BloomFilter, and WebhookFilterStore classes in filter.py.
"""
from __future__ import annotations

import unittest

from causely_notification.field_registry import FIELD_DEFINITIONS
from causely_notification.field_registry import FieldRegistry
from causely_notification.filter import BloomFilter
from causely_notification.filter import FilterIndex
from causely_notification.filter import WebhookFilterStore


class TestBloomFilter(unittest.TestCase):
    def setUp(self):
        self.bloom = BloomFilter(size=100, num_hashes=3)

    def test_add_and_check(self):
        self.bloom.add("apple")
        self.bloom.add("banana")

        self.assertTrue(self.bloom.check("apple"))
        self.assertTrue(self.bloom.check("banana"))
        self.assertFalse(self.bloom.check("cherry"))

    def test_false_positives_possible_but_unlikely(self):
        # Just to ensure basic logic is correct, not a guarantee about false positives.
        self.bloom.add("x")
        self.assertFalse(self.bloom.check("y"))


class TestFilterIndex(unittest.TestCase):
    def setUp(self):
        self.field_registry = FieldRegistry(FIELD_DEFINITIONS)
        self.index = FilterIndex(
            field_registry=self.field_registry, enabled=True,
        )

    def test_add_equals_filter(self):
        # 'equals' operator uses BloomFilter
        self.index.add_filter("severity", "equals", "high")
        self.assertIn("severity", self.index.field_filters)
        self.assertIsNotNone(self.index.field_filters["severity"]["bloom"])
        self.assertEqual(
            len(self.index.field_filters["severity"]["operator"]), 0,
        )

    def test_add_in_filter(self):
        # 'in' operator also uses BloomFilter
        self.index.add_filter(
            "labels.k8s.cluster.name", "in", [
                "prod-cluster", "stage-cluster",
            ],
        )
        self.assertIn("labels.k8s.cluster.name", self.index.field_filters)
        bloom = self.index.field_filters["labels.k8s.cluster.name"]["bloom"]
        self.assertIsNotNone(bloom)
        self.assertTrue(bloom.check("prod-cluster"))
        self.assertTrue(bloom.check("stage-cluster"))
        self.assertFalse(bloom.check("non-existent"))

    def test_add_not_equals_filter(self):
        # 'not_equals' operator uses Operator (no BloomFilter)
        self.index.add_filter("severity", "not_equals", "low")
        self.assertIn("severity", self.index.field_filters)
        self.assertIsNone(self.index.field_filters["severity"]["bloom"])
        self.assertEqual(
            len(self.index.field_filters["severity"]["operator"]), 1,
        )
        op = self.index.field_filters["severity"]["operator"][0]
        self.assertEqual(op["operator"], "not_equals")
        self.assertEqual(op["value"], "low")

    def test_check_payload_with_bloom_and_operator_filters(self):
        # Setup filters: severity=high (bloom), severity != low (operator)
        self.index.add_filter("severity", "equals", "high")
        self.index.add_filter("severity", "not_equals", "low")

        payload = {"severity": "high"}
        self.assertTrue(self.index.check_payload(payload))

        payload = {"severity": "low"}
        # Bloom check passes since severity=low won't fail bloom for 'equals=high', it only fails if payload severity not in bloom.
        # But the operator not_equals low fails because severity=low is the actual field value and we have a not_equals low?
        # Actually, not_equals(low) for severity=low returns False (they're equal), so check_payload should return False.
        self.assertFalse(self.index.check_payload(payload))

    def test_check_payload_with_missing_field(self):
        # If field doesn't exist in payload, bloom or operator checks should gracefully return False if needed
        self.index.add_filter("severity", "equals", "high")
        payload = {}
        # Bloom check fails because severity field_value is None, not in bloom
        self.assertFalse(self.index.check_payload(payload))

    def test_check_payload_with_SLO_computed_field(self):
        # Test computed field (impactsSLO)
        self.index.add_filter("impactsSLO", "equals", True)
        payload = {"slos": {"response_time": "OK"}}
        # impactsSLO is True because slos is in the payload
        self.assertTrue(self.index.check_payload(payload))

        payload = {}
        # impactsSLO is False because slos is not in the payload
        self.assertFalse(self.index.check_payload(payload))


class TestWebhookFilterStore(unittest.TestCase):
    def setUp(self):
        self.store = WebhookFilterStore()

    def test_add_webhook_filters_enabled(self):
        filters = [
            {"field": "severity", "operator": "equals", "value": "high"},
            {
                "field": "labels.k8s.cluster.name",
                "operator": "in", "value": ["prod-cluster"],
            },
        ]
        self.store.add_webhook_filters("webhook1", filters, enabled=True)
        self.assertIn("webhook1", self.store.webhook_filters)

        payload_match = {
            "severity": "high",
            "labels.k8s.cluster.name": "prod-cluster",
        }
        payload_no_match = {
            "severity": "low",
            "labels.k8s.cluster.name": "non-existent",
        }

        result_match = self.store.filter_payload(payload_match)
        self.assertIn("webhook1", result_match)

        result_no_match = self.store.filter_payload(payload_no_match)
        self.assertNotIn("webhook1", result_no_match)

    def test_add_webhook_multi_filters_enabled(self):
        # User added multiple filters for a webhook like severity=high and labels.k8s.cluster.name=prod-cluster
        filters = [
            {"field": "severity", "operator": "equals", "value": "high"},
            {
                "field": "labels.k8s.cluster.name",
                "operator": "in", "value": ["prod-cluster"],
            },
        ]
        self.store.add_webhook_filters("webhook1", filters, enabled=True)
        self.assertIn("webhook1", self.store.webhook_filters)

        # The payload only matches the first filter, but not the second so it should not match webhook1
        payload = {
            "severity": "high",
        }

        result = self.store.filter_payload(payload)
        # This should be empty because the payload does not match all filters
        self.assertEqual([], result)

    def test_add_webhook_filters_disabled(self):
        # If enabled=False, then the webhook acts as a "catch-all" (always returns it)
        filters = [
            {"field": "severity", "operator": "equals", "value": "high"},
        ]
        self.store.add_webhook_filters("webhook2", filters, enabled=False)
        self.assertIn("webhook2", self.store.webhook_filters)

        payload_anything = {
            "severity": "low",
        }

        # Since disabled, we do not actually check the filters
        result = self.store.filter_payload(payload_anything)
        self.assertIn("webhook2", result)

    def test_multiple_webhooks(self):
        # Webhook1 (enabled): severity=high
        self.store.add_webhook_filters(
            "webhook1", [
                {"field": "severity", "operator": "equals", "value": "High"},
            ], enabled=True,
        )

        # Webhook2 (enabled): impactsSLO=True
        self.store.add_webhook_filters(
            "webhook2", [
                {"field": "impactsSLO", "operator": "equals", "value": True},
            ], enabled=True,
        )

        payload = {
            "link": "http://causely.localhost:3000/rootCauses/81703742-b81a-43b0-8509-1e9ac718e2e3",
            "name": "Malfunction",
            "slos": [
                {
                    "status": "AT_RISK",
                    "slo_entity": {
                        "id": "988a33f8-afea-5b3b-b7e7-a578fe5184f1",
                        "link": "http://causely.localhost:3000/topology/988a33f8-afea-5b3b-b7e7-a578fe5184f1",
                        "name": "istio-system/prometheus-RequestSuccessRate",
                        "type": "RatioSLO",
                    },
                    "related_entity": {
                        "id": "6abdca4f-9574-42ec-a6c4-c4ba34f11c92",
                        "link": "http://causely.localhost:3000/topology/6abdca4f-9574-42ec-a6c4-c4ba34f11c92",
                        "name": "istio-system/prometheus",
                        "type": "KubernetesService",
                    },
                },
            ],
            "type": "ProblemDetected",
            "entity": {
                "id": "030fdbc4-8d3b-58f7-aa51-259b75374174",
                "link": "http://causely.localhost:3000/topology/030fdbc4-8d3b-58f7-aa51-259b75374174",
                "name": "istio-system/prometheus-7f467df8b6-zhmqc",
                "type": "ApplicationInstance",
            },
            "labels": {
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.cluster.name": "dev",
                "k8s.namespace.name": "istio-system",
            },
            "objectId": "81703742-b81a-43b0-8509-1e9ac718e2e3",
            "severity": "High",
            "timestamp": "2024-12-13T06:43:08.309296138Z",
            "description": {
                "summary": "An application is experiencing a high rate of errors, causing disruptions for clients. This can lead to degraded performance, failed requests, or complete service unavailability, significantly affecting the user experience.",
                "remediationOptions": [
                    {
                        "title": "Check Logs",
                        "description": "Inspect the container logs for error messages or stack traces, which can provide clues about the issue.\n",
                    },
                ],
            },
        }
        # webhook1 matches because severity=high is in its bloom
        # webhook2 matches because impactsSLO=True is in its bloom
        result = self.store.filter_payload(payload)
        self.assertIn("webhook1", result)
        self.assertIn("webhook2", result)

        payload = {
            "link": "http://causely.localhost:3000/rootCauses/716e46d4-d70a-41f2-b43d-7e65e4dbebc9",
            "name": "CPUCongested",
            "type": "ProblemDetected",
            "entity": {
                "id": "de99f5df-5467-4f82-ab44-656a6085f4a4_kindnet-cni",
                "link": "http://causely.localhost:3000/topology/de99f5df-5467-4f82-ab44-656a6085f4a4_kindnet-cni",
                "name": "kube-system/kindnet/kindnet-cni",
                "type": "ComputeSpec",
            },
            "labels": {
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.cluster.name": "dev",
                "k8s.namespace.name": "kube-system",
            },
            "objectId": "716e46d4-d70a-41f2-b43d-7e65e4dbebc9",
            "severity": "High",
            "timestamp": "2024-12-13T10:51:51.684988421Z",
            "description": {
                "details": "CPU throttling occurs when a container exceeds its CPU quota as defined by Kubernetes or Docker. The container runtime enforces these limits by restricting access to CPU resources, leading to delays in processing tasks. Common causes include insufficient CPU limits/requests for the workload’s demand, high contention for CPU resources from other containers on the same node, or inefficient application behavior such as busy loops or suboptimal thread management.",
                "summary": "One or multiple containers in a workload are experiencing CPU congestion, leading to potential throttling. This occurs when the containers use more CPU resources than allocated, causing degraded performance, longer response times, or application crashes.",
                "remediationOptions": [
                    {
                        "title": "Increase CPU Limits or Requests",
                        "description": "Review and adjust the CPU limits/requests for the affected containers. Ensure that resource requests are aligned with the actual CPU needs of the application. For Kubernetes, update the deployment or pod specification:\n\n```yaml\nresources:\n  requests:\n    cpu: \"500m\"\n  limits:\n    cpu: \"1000m\"\n```\n",
                    },
                    {
                        "title": "Optimize Application Efficiency",
                        "description": "Profile the application to identify inefficiencies in CPU usage, such as excessive thread creation, busy loops, or inefficient algorithms, and address them in the code.\n",
                    },
                    {
                        "title": "Horizontal Pod Scaling",
                        "description": "If CPU demands fluctuate, configure Horizontal Pod Autoscaling (HPA) to automatically scale the number of replicas based on CPU utilization:\n\n```yaml\napiVersion: autoscaling/v2\nkind: HorizontalPodAutoscaler\nspec:\n  maxReplicas: 10\n  metrics:\n  - type: Resource\n    resource:\n      name: cpu\n      targetAverageUtilization: 80\n```\n",
                    },
                ],
            },
        }
        # # webhook1 does match severity=High
        # # webhook2 does not match impactsSLO=False
        result = self.store.filter_payload(payload)
        self.assertIn("webhook1", result)
        self.assertNotIn("webhook2", result)
