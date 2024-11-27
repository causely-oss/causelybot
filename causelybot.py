import json
import os
import sys
from datetime import datetime

import requests
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)


def load_config():
    with open("/etc/causelybot/config.yaml", 'r') as stream:
        return yaml.safe_load(stream)


def get_config():
    return load_config()


def filter_notification(payload):
    # Load the config
    config = get_config()
    payload_name = payload.get("name").lower()  # Normalize case
    payload_entity_type = payload.get("entity", {}).get(
        "type", "").lower()  # Normalize case

    # If the config is not specified or the filter is not enabled, allow the payload
    if not config.get("filterconfig", {}).get("enabled", False):
        return True

    # Get filters from config
    filters = config.get("filterconfig", {}).get("filters", [])

    # Edge case: If filters are not specified correctly, allow all notifications
    if not isinstance(filters, list):
        return True

    # Check if the payload matches any of the filter pairs or partial matches
    for filter_pair in filters:
        allowed_name = filter_pair.get("problemType", "").lower()
        allowed_entity_type = filter_pair.get("entityType", "").lower()

        # Check for full match or partial matches
        if (allowed_name == payload_name or allowed_name == "") and \
           (allowed_entity_type == payload_entity_type or allowed_entity_type == ""):
            return True

    # If no matching filter pair is found, do not allow the payload
    return False


# Environment variables (can be passed as Kubernetes secrets)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
EXPECTED_TOKEN = os.getenv("BEARER_TOKEN")


@app.route('/webhook', methods=['POST'])
def webhook():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        if filter_notification(payload):
            # Forward the payload to Slack
            response = forward_to_slack(payload)
            if response.status_code == 200:
                return jsonify({"message": "Payload forwarded to Slack"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Slack"}), 500
        else:
            return jsonify({"message": "Payload filtered out"}), 200
    else:
        return jsonify({"message": "Unauthorized"}), 401


def parse_iso_date(iso_date_str):
    """
    Parse an ISO 8601 date string and return a human-readable format.

    Args:
        iso_date_str (str): The ISO 8601 date string.

    Returns:
        str: A human-readable date string.
    """
    try:
        # Parse the ISO 8601 date string
        parsed_date = datetime.strptime(iso_date_str[:19], "%Y-%m-%dT%H:%M:%S")
        # Convert to human-readable format
        readable_date = parsed_date.strftime("%B %d, %Y at %I:%M:%S %p")
        return readable_date
    except ValueError as e:
        return iso_date_str


def create_slack_description_block(payload):
    summary = payload.get("description", {}).get("summary", None)
    if summary is None:
        return None

    b = {
        "type": "section",
        "block_id": "block1",
        "text": {
            "type": "mrkdwn",
            "text": f"*Summary:*\n{summary}"
        },
    }
    return b


def create_slack_remediation_option_block(payload):
    ro = payload.get("description", {}).get("remediationOptions", [])
    if len(ro) == 0:
        return None

    b = {
        "type": "section",
        "block_id": "block2",
        "text": {
            "type": "mrkdwn",
            "text": f"*Remediation: {ro[0].get("title")}*\n{ro[0].get("description")}"
        }
    }

    link = payload.get("link", None)
    if len(ro) > 1 and link is not None:
        b["accessory"] = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "View More",
                "emoji": True
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action"
        }

    return b


def create_slack_values_block(payload):
    return {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*Entity:*\n{payload.get('entity', {}).get('name')}"
            },
            {
                "type": "mrkdwn",
                "text": f"*When:*\n{parse_iso_date(payload.get('timestamp'))}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Root Cause:*\n{payload.get("name")}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Severity:*\n{payload.get("severity")}"
            }
        ]
    }


def create_slack_detected_payload(payload):
    blocks = [{
        "type": "rich_text",
        "elements": [{
            "type": "rich_text_section",
            "elements": [{
                "type": "emoji",
                "name": "exclamation"
            }]
        }]
    }, {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Root Cause {payload.get("name")} detected",
        }
    }]

    desc_block = create_slack_description_block(payload)
    if desc_block is not None:
        blocks.append(desc_block)
        blocks.append({
            "type": "divider"
        })

    rem_block = create_slack_remediation_option_block(payload)
    if rem_block is not None:
        blocks.append(rem_block)
        blocks.append({
            "type": "divider"
        })

    blocks.append(create_slack_values_block(payload))
    blocks.append({
        "type": "divider"
    })

    buttons = []

    link = payload.get("link", None)
    if link is not None:
        buttons.append({
            "type": "button",
            "text": {
                    "type": "plain_text",
                    "text": "View Root Cause",
                    "emoji": True
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action"
        })

    buttons.append({
        "type": "button",
        "text": {
                "type": "plain_text",
                "emoji": True,
                "text": "Silence"
        },
        "style": "primary",
        "value": "silence"
    })

    blocks.append({
        "type": "actions",
        "elements": buttons,
    })

    return blocks


def create_slack_cleared_payload(payload):
    blocks = [{
        "type": "rich_text",
        "elements": [{
            "type": "rich_text_section",
            "elements": [{
                "type": "emoji",
                "name": "white_check_mark"
            }]
        }]
    }, {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"Root Cause {payload.get("name")} cleared",
        }
    }]

    desc_block = create_slack_description_block(payload)
    if desc_block is not None:
        blocks.append(desc_block)
        blocks.append({
            "type": "divider"
        })

    blocks.append(create_slack_values_block(payload))
    blocks.append({
        "type": "divider"
    })

    buttons = []

    link = payload.get("link", None)
    if link is not None:
        buttons.append({
            "type": "button",
            "text": {
                    "type": "plain_text",
                    "text": "View Root Cause",
                    "emoji": True
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action"
        })

        blocks.append({
            "type": "actions",
            "elements": buttons,
        })

    return blocks


def forward_to_slack(payload):
    # Prettify the payload and send it to Slack
    print(payload, file=sys.stderr)
    print(payload.get("type"), file=sys.stderr)

    if payload.get("type") == "ProblemDetected":
        slack_data = {
            "username": "Causely",
            "icon_emoji": ":causely:",
            "blocks": create_slack_detected_payload(payload),
        }
    else:
        slack_data = {
            "username": "Causely",
            "icon_emoji": ":causely:",
            "blocks": create_slack_cleared_payload(payload),
        }

    print(json.dumps(slack_data), file=sys.stderr)

    headers = {'Content-Type': 'application/json'}
    return requests.post(SLACK_WEBHOOK_URL, json=slack_data, headers=headers)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
