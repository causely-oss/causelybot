import json
import os
import sys

import requests
import yaml

from .date import parse_iso_date

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


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
            "text": f"*Remediation: {ro[0].get('title')}*\n{ro[0].get('description')}"
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
                "text": f"*Root Cause:*\n{payload.get('name')}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Severity:*\n{payload.get('severity')}"
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
            "text": f"Root Cause {payload.get('name')} detected",
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
            "text": f"Root Cause {payload.get('name')} cleared",
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
