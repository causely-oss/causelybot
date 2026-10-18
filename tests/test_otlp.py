# Tests for causely_notification.otlp (forward_to_otlp)
import json
import unittest
from unittest.mock import MagicMock, patch

from causely_notification.otlp import (
    build_logs_url,
    create_otlp_logs_payload,
    forward_to_otlp,
    timestamp_to_nanos,
)


class TestOtlpHelpers(unittest.TestCase):

    def test_build_logs_url_strips_trailing_slash(self):
        self.assertEqual(
            build_logs_url("https://otel.example.com:4318/"),
            "https://otel.example.com:4318/v1/logs",
        )

    def test_build_logs_url_without_trailing_slash(self):
        self.assertEqual(
            build_logs_url("https://otel.example.com:4318"),
            "https://otel.example.com:4318/v1/logs",
        )


class TestCreateOtlpLogsPayload(unittest.TestCase):

    def test_detected_payload_structure(self):
        payload = {
            "link": "https://portal.causely.app/rootCauses/abc",
            "name": "ImagePullErrors",
            "type": "ProblemDetected",
            "entity": {
                "id": "entity-id",
                "name": "default/pull-error-demo-2",
                "type": "Controller",
            },
            "labels": {
                "k8s.cluster.name": "dev",
                "k8s.namespace.name": "default",
            },
            "objectId": "abc",
            "severity": "High",
            "timestamp": "2026-04-28T19:28:31.686364684Z",
            "description": {
                "summary": "Image pull errors detected.",
                "remediationOptions": [
                    {"title": "Check Image", "description": "Verify image tag."}
                ],
            },
        }

        otlp_payload = create_otlp_logs_payload(payload)
        log_record = otlp_payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]

        self.assertIn("Root cause identified: ImagePullErrors", log_record["body"]["stringValue"])
        self.assertEqual(log_record["severityNumber"], 17)
        self.assertEqual(log_record["severityText"], "ERROR")
        self.assertEqual(log_record["timeUnixNano"], timestamp_to_nanos(payload["timestamp"]))

        attrs = {a["key"]: a["value"]["stringValue"] for a in log_record["attributes"]}
        self.assertEqual(attrs["causely.type"], "ProblemDetected")
        self.assertEqual(attrs["causely.name"], "ImagePullErrors")
        self.assertEqual(attrs["causely.severity"], "High")
        self.assertEqual(attrs["causely.summary"], "Image pull errors detected.")
        self.assertIn("ImagePullErrors", attrs["causely.payload"])

        resource_attrs = {
            a["key"]: a["value"]["stringValue"]
            for a in otlp_payload["resourceLogs"][0]["resource"]["attributes"]
        }
        self.assertEqual(resource_attrs["service.name"], "default/pull-error-demo-2")
        self.assertEqual(resource_attrs["k8s.cluster.name"], "dev")
        self.assertEqual(resource_attrs["k8s.namespace.name"], "default")

    def test_problem_updated_treated_like_detected(self):
        payload = {
            "name": "Malfunction",
            "type": "ProblemUpdated",
            "entity": {"name": "my-service"},
            "severity": "Critical",
            "timestamp": "2026-04-28T19:28:31Z",
        }

        otlp_payload = create_otlp_logs_payload(payload)
        log_record = otlp_payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]

        self.assertIn("Root cause identified", log_record["body"]["stringValue"])
        self.assertEqual(log_record["severityNumber"], 21)
        self.assertEqual(log_record["severityText"], "FATAL")

    def test_cleared_payload_structure(self):
        payload = {
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {"name": "my-service"},
            "severity": "Low",
            "timestamp": "2026-04-28T20:00:00Z",
            "duration_ns": 601639777492,
        }

        otlp_payload = create_otlp_logs_payload(payload)
        log_record = otlp_payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]

        self.assertIn("Root cause cleared: Congested", log_record["body"]["stringValue"])
        self.assertEqual(log_record["severityNumber"], 9)
        self.assertEqual(log_record["severityText"], "INFO")

        attrs = {a["key"]: a["value"]["stringValue"] for a in log_record["attributes"]}
        self.assertEqual(attrs["causely.type"], "ProblemCleared")
        self.assertEqual(attrs["causely.duration_ns"], "601639777492")


class TestForwardToOtlp(unittest.TestCase):

    @patch("causely_notification.otlp.requests.post")
    def test_forward_to_otlp_detected(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {"name": "my-service"},
            "severity": "High",
            "timestamp": "2026-04-28T19:28:31Z",
            "description": {"summary": "High error rate."},
        }
        base_url = "https://otel.example.com:4318"
        token = "fake-otlp-token"

        response = forward_to_otlp(payload, base_url, token)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_post.call_count, 1)
        call_url = mock_post.call_args[0][0]
        self.assertEqual(call_url, "https://otel.example.com:4318/v1/logs")

        body = mock_post.call_args[1]["json"]
        log_record = body["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        self.assertIn("Root cause identified", log_record["body"]["stringValue"])

        attrs = {a["key"]: a["value"]["stringValue"] for a in log_record["attributes"]}
        self.assertEqual(json.loads(attrs["causely.payload"])["name"], "Malfunction")

        headers = mock_post.call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer fake-otlp-token")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("causely_notification.otlp.requests.post")
    def test_forward_to_otlp_cleared(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {"name": "my-service"},
            "severity": "Low",
            "timestamp": "2026-04-28T20:00:00Z",
        }

        response = forward_to_otlp(payload, "https://otel.example.com:4318", "token")

        self.assertEqual(response.status_code, 200)
        body = mock_post.call_args[1]["json"]
        log_record = body["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        self.assertIn("Root cause cleared", log_record["body"]["stringValue"])

    @patch("causely_notification.otlp.requests.post")
    def test_forward_to_otlp_without_token(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {"name": "my-service"},
            "severity": "High",
            "timestamp": "2026-04-28T19:28:31Z",
        }

        forward_to_otlp(payload, "https://otel.example.com:4318")

        headers = mock_post.call_args[1]["headers"]
        self.assertNotIn("Authorization", headers)
