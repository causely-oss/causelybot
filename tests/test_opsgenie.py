# Tests for causely_notification.opsgenie (forward_to_opsgenie)
import unittest
from unittest.mock import patch, MagicMock

from causely_notification.opsgenie import forward_to_opsgenie


class TestForwardToOpsgenie(unittest.TestCase):

    @patch("causely_notification.opsgenie.requests.post")
    def test_forward_to_opsgenie_detected(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        payload = {
            "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "name": "/webhook/opsgenie",
                "type": "HTTPPath"
            },
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "Critical",
            "timestamp": "2025-08-07T18:51:54.164185287Z",
            "description": {
                "summary": "The HTTP path is experiencing a high rate of errors...",
                "remediationOptions": [
                    {"title": "Check Logs", "description": "Inspect the application logs..."}
                ]
            }
        }
        url = "https://api.opsgenie.com/v2/alerts"
        api_key = "fake-opsgenie-key"

        response = forward_to_opsgenie(payload, url, api_key)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(mock_post.call_count, 1)
        call_url = mock_post.call_args[0][0]
        self.assertEqual(call_url, url)
        body = mock_post.call_args[1]["json"]
        self.assertIn("message", body)
        self.assertIn("Malfunction", body["message"])
        self.assertIn("Root Cause Identified", body["message"])
        self.assertEqual(body["priority"], "CRITICAL")
        self.assertIn("description", body)
        self.assertIn("The HTTP path is experiencing", body["description"])
        headers = mock_post.call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "GenieKey fake-opsgenie-key")

    @patch("causely_notification.opsgenie.requests.post")
    def test_forward_to_opsgenie_cleared(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        payload = {
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {"name": "my-service"},
            "severity": "Low",
            "timestamp": "2025-08-07T19:00:00Z",
            "description": {"summary": "Issue resolved."}
        }
        url = "https://api.opsgenie.com/v2/alerts"
        api_key = "fake-key"

        response = forward_to_opsgenie(payload, url, api_key)

        self.assertEqual(response.status_code, 202)
        body = mock_post.call_args[1]["json"]
        self.assertIn("Root Cause Cleared", body["message"])
        self.assertIn("Congested", body["message"])
        self.assertEqual(body["priority"], "LOW")
