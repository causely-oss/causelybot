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

# Tests for causely_notification.debug (forward_to_debug)
import unittest
from unittest.mock import patch
from io import StringIO

from causely_notification.debug import forward_to_debug


class TestForwardToDebug(unittest.TestCase):

    @patch('sys.stderr', new_callable=StringIO)
    def test_forward_to_debug_problem_detected(self, mock_stderr):
        """Test debug webhook with ProblemDetected notification."""
        payload = {
            "link": "https://portal.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "link": "https://portal.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "name": "test-service",
                "type": "KubernetesService"
            },
            "labels": {
                "k8s.cluster.name": "test-cluster",
                "k8s.namespace.name": "default"
            },
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "High",
            "timestamp": "2025-08-07T18:51:54.164185287Z",
            "description": {
                "summary": "The service is experiencing a high rate of errors.",
                "remediationOptions": [
                    {
                        "title": "Check Logs",
                        "description": "Inspect the application logs for error messages."
                    }
                ]
            }
        }

        response = forward_to_debug(payload, url="https://test.example.com/webhook", token="test-token-123")

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertIn("Debug output printed to stderr", response.content)

        # Verify debug output contains key information
        output = mock_stderr.getvalue()
        self.assertIn("DEBUG WEBHOOK", output)
        self.assertIn("https://test.example.com/webhook", output)
        self.assertIn("length=14", output)  # Length of "test-token-123"
        self.assertNotIn("test-token-123", output)  # Token value should not appear
        self.assertIn("ProblemDetected", output)
        self.assertIn("Malfunction", output)
        self.assertIn("High", output)
        self.assertIn("test-service", output)
        self.assertIn("KubernetesService", output)
        self.assertIn("The service is experiencing a high rate of errors", output)
        self.assertIn("k8s.cluster.name", output)
        self.assertIn("test-cluster", output)

    @patch('sys.stderr', new_callable=StringIO)
    def test_forward_to_debug_problem_cleared(self, mock_stderr):
        """Test debug webhook with ProblemCleared notification."""
        payload = {
            "link": "https://portal.causely.app/rootCauses/71dd427c-c95e-45b1-a72e-db2d15a3eb58",
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {
                "id": "90719b30-95b3-5eac-8601-58813910ddb6",
                "link": "https://portal.causely.app/observe/topology/90719b30-95b3-5eac-8601-58813910ddb6",
                "name": "my-service",
                "type": "Service"
            },
            "labels": {
                "k8s.cluster.name": "prod-cluster"
            },
            "objectId": "71dd427c-c95e-45b1-a72e-db2d15a3eb58",
            "severity": "Medium",
            "timestamp": "2025-08-07T19:07:29.416709Z",
            "description": {
                "summary": "The service congestion has been cleared.",
            },
            "duration_ns": 369506251438
        }

        response = forward_to_debug(payload, url="https://webhook.example.com", token="abc123")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify debug output
        output = mock_stderr.getvalue()
        self.assertIn("ProblemCleared", output)
        self.assertIn("Congested", output)
        self.assertIn("Medium", output)
        self.assertIn("my-service", output)
        self.assertIn("https://webhook.example.com", output)
        self.assertIn("length=6", output)  # Length of "abc123"

    @patch('sys.stderr', new_callable=StringIO)
    def test_forward_to_debug_with_slos(self, mock_stderr):
        """Test debug webhook with SLO information."""
        payload = {
            "link": "https://portal.causely.app/rootCauses/test-123",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "entity-123",
                "name": "api-service",
                "type": "Service"
            },
            "objectId": "test-123",
            "severity": "Critical",
            "timestamp": "2025-08-07T20:00:00Z",
            "description": {
                "summary": "Service is experiencing errors."
            },
            "slos": [
                {
                    "status": "AT_RISK",
                    "slo_entity": {
                        "id": "slo-1",
                        "name": "api-availability-slo",
                        "type": "RatioSLO"
                    },
                    "related_entity": {
                        "id": "service-1",
                        "name": "api-service",
                        "type": "KubernetesService"
                    }
                },
                {
                    "status": "VIOLATED",
                    "slo_entity": {
                        "id": "slo-2",
                        "name": "api-latency-slo",
                        "type": "LatencySLO"
                    },
                    "related_entity": {
                        "id": "service-1",
                        "name": "api-service",
                        "type": "KubernetesService"
                    }
                }
            ]
        }

        response = forward_to_debug(payload, url="https://slo.example.com/hook", token="slo-token-xyz")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify SLO output
        output = mock_stderr.getvalue()
        self.assertIn("Impacted SLOs (2)", output)
        self.assertIn("api-availability-slo", output)
        self.assertIn("AT_RISK", output)
        self.assertIn("api-latency-slo", output)
        self.assertIn("VIOLATED", output)

    @patch('sys.stderr', new_callable=StringIO)
    def test_forward_to_debug_minimal_payload(self, mock_stderr):
        """Test debug webhook with minimal payload."""
        payload = {
            "type": "ProblemDetected",
            "name": "Test Problem"
        }

        response = forward_to_debug(payload, url="https://minimal.example.com")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify it handles missing fields gracefully
        output = mock_stderr.getvalue()
        self.assertIn("ProblemDetected", output)
        self.assertIn("Test Problem", output)
        self.assertIn("Unknown", output)  # Should show Unknown for missing fields
        self.assertIn("https://minimal.example.com", output)
        self.assertIn("not provided", output)  # No token provided

    @patch('sys.stderr', new_callable=StringIO)
    def test_forward_to_debug_shows_url_and_token_info(self, mock_stderr):
        """Test that debug webhook shows URL and token information securely."""
        payload = {
            "type": "ProblemDetected",
            "name": "Test Problem",
            "entity": {
                "id": "test-id",
                "name": "test-entity",
                "type": "Service"
            },
            "severity": "Low",
            "timestamp": "2025-08-07T20:00:00Z"
        }

        # Call with URL and token
        response = forward_to_debug(payload, url="https://example.com/webhook", token="secret-1234567890")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify output shows URL and token length but not token value
        output = mock_stderr.getvalue()
        self.assertIn("Test Problem", output)
        self.assertIn("test-entity", output)
        self.assertIn("https://example.com/webhook", output)
        self.assertIn("length=17", output)  # Length of "secret-1234567890"
        self.assertNotIn("secret-1234567890", output)  # Token value should not appear
        self.assertIn("Would send", output)  # Indicates it would send but doesn't


if __name__ == '__main__':
    unittest.main()
