# server_test.py
from unittest.mock import patch, Mock

import yaml
import os
import textwrap
os.environ["URL_SLACK-ALL-ALERTS"] = "http://test_slack"
os.environ["URL_SLACK-MALFUNCTION-SLO"] = "http://test_slack"
os.environ["URL_SLACK-SEVERITY"] = "http://test_slack"
os.environ["AUTH_TOKEN"] = "test-token"

from causely_notification.server import app
from causely_notification.server import populate_webhooks
from causely_notification import server

test_payload = {
    "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "name": "Malfunction",
    "type": "ProblemDetected",
    "entity": {
        "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "name": "/webhook/teams",
        "type": "HTTPPath"
    },
    "labels": {
        "causely.ai/service-id": "fdea69a6-7ae3-504c-a5f9-cd450d135672",
        "causely.ai/service-name": "causelybot"
    },
    "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "severity": "High",
    "timestamp": "2025-08-07T18:51:54.164185287Z",
    "description": {
        "details": "A higher error rate can stem from multiple factors...",
        "summary": "The HTTP path is experiencing a high rate of errors...",
        "remediationOptions": [
            {"title": "Check Logs", "description": "Inspect the application logs..."}
        ]
    }
}

test_payload_update = {
    "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "name": "Malfunction",
    "type": "ProblemUpdated",
    "entity": {
        "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "name": "/webhook/teams",
        "type": "HTTPPath"
    },
    "labels": {
        "causely.ai/service-id": "fdea69a6-7ae3-504c-a5f9-cd450d135672",
        "causely.ai/service-name": "causelybot"
    },
    "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "severity": "High",
    "old_severity": "Low",
    "timestamp": "2025-08-07T18:51:54.164185287Z",
    "description": {
        "details": "A higher error rate can stem from multiple factors...",
        "summary": "The HTTP path is experiencing a high rate of errors...",
        "remediationOptions": [
            {"title": "Check Logs", "description": "Inspect the application logs..."}
        ]
    }
}

test_payload_update_lower = {
    "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "name": "Malfunction",
    "type": "ProblemUpdated",
    "entity": {
        "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "name": "/webhook/teams",
        "type": "HTTPPath"
    },
    "labels": {
        "causely.ai/service-id": "fdea69a6-7ae3-504c-a5f9-cd450d135672",
        "causely.ai/service-name": "causelybot"
    },
    "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "severity": "Low",
    "old_severity": "High",
    "timestamp": "2025-08-07T18:51:54.164185287Z",
    "description": {
        "details": "A higher error rate can stem from multiple factors...",
        "summary": "The HTTP path is experiencing a high rate of errors...",
        "remediationOptions": [
            {"title": "Check Logs", "description": "Inspect the application logs..."}
        ]
    }
}

test_payload_update_same = {
    "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "name": "Malfunction",
    "type": "ProblemUpdated",
    "entity": {
        "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
        "name": "/webhook/teams",
        "type": "HTTPPath"
    },
    "labels": {
        "causely.ai/service-id": "fdea69a6-7ae3-504c-a5f9-cd450d135672",
        "causely.ai/service-name": "causelybot"
    },
    "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
    "severity": "High",
    "old_severity": "High",
    "timestamp": "2025-08-07T18:51:54.164185287Z",
    "description": {
        "details": "A higher error rate can stem from multiple factors...",
        "summary": "The HTTP path is experiencing a high rate of errors...",
        "remediationOptions": [
            {"title": "Check Logs", "description": "Inspect the application logs..."}
        ]
    }
}

test_payload_for_filters = {
	"link": "https://portal.causely.app",
	"name": "Causely: Test Notification 20",
	"type": "ProblemCleared",
	"entity": {
		"id": "2c990ff-7c5c-5a4f-a004-f6a1a9a58b85",
		"link": "https://portal.causely.app",
		"name": "the-most-important-service",
		"type": "Node"
	},
	"labels": {
		"k8s.cluster.name": "my-important-services-cluster",
		"gcp.resource.zone": "https://www.googleapis.com/compute/v1/projects/example-project/zones/us-central1-a",
		"causely.ai/cluster": "production"
	},
	"objectId": "2ac21477-61f3-4ae0-9fc4-0c1ea43ff727",
	"severity": "Critical",
	"timestamp": "2025-06-27T19:15:16.410543344Z",
	"description": {
		"details": "UI Test Notification",
		"summary": "UI Test Notification."
	}
}

yaml_text = textwrap.dedent("""
webhooks:
  - name: "slack-severity"
    url: "https://hooks.slack.com/services/T00000000/B00000001/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
    hook_type: slack
    filters:
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
  - name: "slack-malfunction-slo"
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
    hook_type: slack
    filters:
      enabled: true
      values:
        - field: "name"
          operator: "equals"
          value: "Malfunction"
        - field: "impactsSLO"
          operator: "equals"
          value: true
""")

config_test_yaml = textwrap.dedent("""
webhooks:
  - name: "slack-all-alerts" # Required
    hook_type: "slack" # Required [slack, teams, jira, opsgenie]
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    filters: # Optional - see Filtering Notifications
      enabled: true
      values:
        - field: "labels.k8s.cluster.name"
          operator: "in"
          value: ["my-important-services-cluster"]
""")

@patch("requests.post")
# Mock post to webhooks with 1 matching webhook
def test_webhook_posts_expected_payload(mock_post):
    # 2) minimal stub for SECOND call (only to avoid network / errors)
    second_resp = Mock(status_code=202)
    second_resp.json.return_value = {"ok": True}
    second_resp.raise_for_status.return_value = None

    mock_post.side_effect = [second_resp]

    webhook_data = yaml.safe_load(yaml_text)
    webhooks = webhook_data.get("webhooks")

    filter_store, webhook_lookup_map = populate_webhooks(webhooks)
    server.filter_store = filter_store
    server.webhook_lookup_map = webhook_lookup_map
    client = app.test_client()
    resp = client.post("/webhook", json=test_payload, headers={"Authorization": "Bearer test-token"})  # this sets flask.request for you
    assert resp.status_code == 200

    # Assertions
    assert mock_post.call_count == 1

    # Second call URL
    second_url = "http://test_slack"
    url2 = mock_post.call_args_list[0].args[0]
    assert url2 == second_url

# Mock post to webhooks that is an update - severity going up
@patch("requests.post")
def test_webhook_posts_expected_payload2(mock_post):
    # 2) minimal stub for SECOND call (only to avoid network / errors)
    second_resp = Mock(status_code=202)
    second_resp.json.return_value = {"ok": True}
    second_resp.raise_for_status.return_value = None

    mock_post.side_effect = [second_resp]

    webhook_data = yaml.safe_load(yaml_text)
    webhooks = webhook_data.get("webhooks")

    filter_store, webhook_lookup_map = populate_webhooks(webhooks)
    server.filter_store = filter_store
    server.webhook_lookup_map = webhook_lookup_map
    client = app.test_client()
    resp = client.post("/webhook", json=test_payload_update, headers={"Authorization": "Bearer test-token"})  # this sets flask.request for you
    assert resp.status_code == 200

    # Assertions
    assert mock_post.call_count == 1

    # Second call URL
    second_url = "http://test_slack"
    url2 = mock_post.call_args_list[0].args[0]
    assert url2 == second_url

# Mock post to webhooks that is an update - severity going down
@patch("requests.post")
def test_webhook_posts_expected_payload3(mock_post):
    # 2) minimal stub for SECOND call (only to avoid network / errors)
    second_resp = Mock(status_code=202)
    second_resp.json.return_value = {"ok": True}
    second_resp.raise_for_status.return_value = None

    mock_post.side_effect = [second_resp]

    webhook_data = yaml.safe_load(yaml_text)
    webhooks = webhook_data.get("webhooks")

    filter_store, webhook_lookup_map = populate_webhooks(webhooks)
    server.filter_store = filter_store
    server.webhook_lookup_map = webhook_lookup_map
    client = app.test_client()
    resp = client.post("/webhook", json=test_payload_update_lower, headers={"Authorization": "Bearer test-token"})  # this sets flask.request for you
    assert resp.status_code == 200

    # Assertions
    assert mock_post.call_count == 1

    # Second call URL
    second_url = "http://test_slack"
    url2 = mock_post.call_args_list[0].args[0]
    assert url2 == second_url

# Mock post to webhooks that is an update - severity same - no post to slack
@patch("requests.post")
def test_webhook_posts_expected_payload4(mock_post):
    # 2) minimal stub for SECOND call (only to avoid network / errors)
    second_resp = Mock(status_code=202)
    second_resp.json.return_value = {"ok": True}
    second_resp.raise_for_status.return_value = None

    mock_post.side_effect = [second_resp]

    webhook_data = yaml.safe_load(yaml_text)
    webhooks = webhook_data.get("webhooks")

    filter_store, webhook_lookup_map = populate_webhooks(webhooks)
    server.filter_store = filter_store
    server.webhook_lookup_map = webhook_lookup_map
    client = app.test_client()
    resp = client.post("/webhook", json=test_payload_update_same, headers={"Authorization": "Bearer test-token"})  # this sets flask.request for you
    assert resp.status_code == 200

    # Assertions
    assert mock_post.call_count == 0

@patch("requests.post")
# Mock post to webhooks with 1 matching webhook
def test_webhook_posts_expected_payload_filtered(mock_post):
    # 2) minimal stub for SECOND call (only to avoid network / errors)
    second_resp = Mock(status_code=202)
    second_resp.json.return_value = {"ok": True}
    second_resp.raise_for_status.return_value = None

    mock_post.side_effect = [second_resp]

    webhook_data = yaml.safe_load(config_test_yaml)
    webhooks = webhook_data.get("webhooks")

    filter_store, webhook_lookup_map = populate_webhooks(webhooks)
    server.filter_store = filter_store
    server.webhook_lookup_map = webhook_lookup_map
    client = app.test_client()
    resp = client.post("/webhook", json=test_payload_for_filters, headers={"Authorization": "Bearer test-token"})  # this sets flask.request for you
    assert resp.status_code == 200

    # Assertions
    assert mock_post.call_count == 1

    # Second call URL
    second_url = "http://test_slack"
    url2 = mock_post.call_args_list[0].args[0]
    assert url2 == second_url
