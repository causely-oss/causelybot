# Tests for causely_notification.jira (forward_to_jira)
import unittest
from unittest.mock import patch, MagicMock

from causely_notification.jira import forward_to_jira


class TestForwardToJira(unittest.TestCase):

    @patch("causely_notification.jira.requests.post")
    def test_forward_to_jira_detected(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        payload = {
            "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "name": "/webhook/jira",
                "type": "HTTPPath"
            },
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "High",
            "timestamp": "2025-08-07T18:51:54.164185287Z",
            "description": {
                "summary": "The HTTP path is experiencing a high rate of errors...",
                "remediationOptions": [
                    {"title": "Check Logs", "description": "Inspect the application logs..."}
                ]
            }
        }
        url = "https://fake.atlassian.net"
        token = "fake-jira-token"

        response = forward_to_jira(payload, url, token)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_post.call_count, 1)
        call_url = mock_post.call_args[0][0]
        self.assertEqual(call_url, f"{url}/rest/api/2/issue")
        body = mock_post.call_args[1]["json"]
        self.assertIn("fields", body)
        self.assertIn("Malfunction", body["fields"]["summary"])
        self.assertIn("Root Cause Identified", body["fields"]["summary"])
        self.assertIn("The HTTP path is experiencing", body["fields"]["description"])
        self.assertIn("Check Logs", body["fields"]["description"])

    @patch("causely_notification.jira.requests.post")
    def test_forward_to_jira_cleared(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        payload = {
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {"name": "my-service", "link": "https://example.com"},
            "severity": "Medium",
            "timestamp": "2025-08-07T19:00:00Z",
            "description": {"summary": "Issue resolved."}
        }
        url = "https://fake.atlassian.net"
        token = "fake-jira-token"

        response = forward_to_jira(payload, url, token)

        self.assertEqual(response.status_code, 201)
        body = mock_post.call_args[1]["json"]
        self.assertIn("Root Cause Cleared", body["fields"]["summary"])
        self.assertIn("Congested", body["fields"]["summary"])
