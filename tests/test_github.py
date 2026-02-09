# Tests for causely_notification.github (forward_to_github)
import unittest
from unittest.mock import patch, MagicMock

from causely_notification.github import (
    RC_ID_MARKER,
    forward_to_github,
)


class TestForwardToGitHub(unittest.TestCase):

    @patch("causely_notification.github.requests.request")
    def test_forward_to_github_problem_detected_creates_issue(self, mock_request):
        # First call: list issues (empty). Second call: create issue.
        # github_request returns resp.json() if resp.content else None — need truthy content
        mock_request.side_effect = [
            MagicMock(ok=True, status_code=200, content=b"[]", json=lambda: []),
            MagicMock(
                ok=True,
                status_code=201,
                content=b" ",
                json=lambda: {
                    "number": 42,
                    "html_url": "https://github.com/owner/repo/issues/42",
                },
            ),
        ]

        payload = {
            "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "name": "/webhook/github",
                "type": "HTTPPath",
            },
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "High",
            "timestamp": "2025-08-07T18:51:54.164185287Z",
            "description": {
                "summary": "The HTTP path is experiencing a high rate of errors...",
                "details": "A higher error rate can stem from multiple factors...",
                "remediationOptions": [
                    {"title": "Check Logs", "description": "Inspect the application logs..."}
                ],
            },
        }
        repo_spec = "owner/repo"
        token = "fake-github-token"

        response = forward_to_github(payload, repo_spec, token)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_request.call_count, 2)
        # First call: GET list issues
        self.assertEqual(mock_request.call_args_list[0].args[0], "GET")
        self.assertIn("/repos/owner/repo/issues", mock_request.call_args_list[0].args[1])
        # Second call: POST create issue
        self.assertEqual(mock_request.call_args_list[1].args[0], "POST")
        create_url = mock_request.call_args_list[1].args[1]
        self.assertEqual(create_url, "https://api.github.com/repos/owner/repo/issues")
        body = mock_request.call_args_list[1].kwargs["json"]
        self.assertIn("title", body)
        self.assertIn("[Causely]", body["title"])
        self.assertIn("Malfunction", body["title"])
        self.assertIn("body", body)
        self.assertIn(RC_ID_MARKER + payload["objectId"], body["body"])
        self.assertIn("The HTTP path is experiencing", body["body"])
        self.assertIn("Check Logs", body["body"])

    @patch("causely_notification.github.requests.request")
    def test_forward_to_github_problem_updated_creates_issue(self, mock_request):
        mock_request.side_effect = [
            MagicMock(ok=True, status_code=200, content=b"[]", json=lambda: []),
            MagicMock(
                ok=True,
                status_code=201,
                content=b" ",
                json=lambda: {"number": 1, "html_url": "https://github.com/foo/bar/issues/1"},
            ),
        ]

        payload = {
            "name": "Congested",
            "type": "ProblemUpdated",
            "entity": {"name": "my-service", "id": "svc-1"},
            "objectId": "rc-123",
            "severity": "Medium",
            "timestamp": "2025-08-07T19:00:00Z",
            "description": {"summary": "Issue updated."},
        }
        response = forward_to_github(payload, "foo/bar", "token")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_request.call_count, 2)
        body = mock_request.call_args_list[1].kwargs["json"]
        self.assertIn("[Causely]", body["title"])
        self.assertIn("Congested", body["title"])
        self.assertIn(RC_ID_MARKER + "rc-123", body["body"])

    @patch("causely_notification.github.requests.request")
    def test_forward_to_github_problem_cleared_ignored(self, mock_request):
        payload = {
            "name": "Congested",
            "type": "ProblemCleared",
            "entity": {"name": "my-service"},
            "objectId": "rc-456",
            "severity": "Low",
            "timestamp": "2025-08-07T19:00:00Z",
            "description": {"summary": "Issue resolved."},
        }
        response = forward_to_github(payload, "owner/repo", "token")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "ignored event type")
        mock_request.assert_not_called()

    @patch("causely_notification.github.requests.request")
    def test_forward_to_github_existing_issue_skipped(self, mock_request):
        existing_body = "Some text\n" + RC_ID_MARKER + "d76f027d-e697-46ed-8a2c-f16356a97ceb"
        mock_request.return_value = MagicMock(
            ok=True,
            status_code=200,
            content=b" ",  # truthy so github_request returns resp.json()
            json=lambda: [
                {
                    "number": 10,
                    "html_url": "https://github.com/owner/repo/issues/10",
                    "body": existing_body,
                    "pull_request": None,
                }
            ],
        )

        payload = {
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {"name": "svc"},
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "High",
            "timestamp": "2025-08-07T18:51:54Z",
            "description": {"summary": "Summary."},
        }
        response = forward_to_github(payload, "owner/repo", "token")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "existing")
        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(mock_request.call_args_list[0].args[0], "GET")

    def test_forward_to_github_invalid_repo_spec_returns_500(self):
        payload = {
            "type": "ProblemDetected",
            "objectId": "rc-1",
            "name": "Test",
            "entity": {},
            "description": {},
        }
        response = forward_to_github(payload, "invalid", "token")
        self.assertEqual(response.status_code, 500)
        self.assertIn("owner/repo", response.text)

    def test_forward_to_github_missing_object_id_returns_400(self):
        payload = {
            "type": "ProblemDetected",
            "name": "Test",
            "entity": {},
            "description": {},
        }
        response = forward_to_github(payload, "owner/repo", "token")
        self.assertEqual(response.status_code, 400)
        self.assertIn("objectId", response.text)
