from __future__ import annotations

import json
import sys

import requests

from .date import parse_iso_date


def create_slack_description_block(payload):
    summary = payload.get("description", {}).get("summary", None)
    if summary is None:
        return None

    b = {
        "type": "section",
        "block_id": "block1",
        "text": {
            "type": "mrkdwn",
            "text": f"*Summary:*\n{summary}",
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
            "text": f"*Remediation: {ro[0].get('title')}*\n{ro[0].get('description')}",
        },
    }

    link = payload.get("link", None)
    if len(ro) > 1 and link is not None:
        b["accessory"] = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "View More",
                "emoji": True,
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action",
        }

    return b


def create_slack_slo_blocks(payload):
    slos = payload.get("slos", [])
    if not slos:
        return None

    # We'll return multiple blocks: a header and a section for each SLO
    blocks = []

    # Add a header for impacted SLOs
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Impacted SLOs",
        },
    })

    # Add each SLO as a section block
    for slo in slos:
        slo_entity = slo.get("slo_entity", {})
        slo_name = slo_entity.get("name", "Unknown SLO")
        slo_link = slo_entity.get("link")
        slo_status = slo.get("status", "UNKNOWN")

        # Construct the text line
        # Example: "*AT_RISK*: <http://link|istio-system/prometheus-RequestSuccessRate>"
        slo_text = f"*{slo_status}*: "
        if slo_link:
            slo_text += f"<{slo_link}|{slo_name}>"
        else:
            slo_text += slo_name

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": slo_text,
            },
        })

    return blocks


def create_slack_values_block(payload):
    return {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*Entity:*\n{payload.get('entity', {}).get('name')}",
            },
            {
                "type": "mrkdwn",
                "text": f"*When:*\n{parse_iso_date(payload.get('timestamp'))}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Root Cause:*\n{payload.get('name')}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Severity:*\n{payload.get('severity')}",
            },
        ],
    }


def create_slack_detected_payload(payload):
    blocks = [
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "emoji",
                    "name": "exclamation",
                }],
            }],
        }, {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Root Cause {payload.get('name')} detected",
            },
        },
    ]

    desc_block = create_slack_description_block(payload)
    if desc_block is not None:
        blocks.append(desc_block)
        blocks.append({
            "type": "divider",
        })

    rem_block = create_slack_remediation_option_block(payload)
    if rem_block is not None:
        blocks.append(rem_block)
        blocks.append({
            "type": "divider",
        })

    # Add SLO blocks if they exist
    slo_blocks = create_slack_slo_blocks(payload)
    if slo_blocks is not None:
        blocks.extend(slo_blocks)
        blocks.append({"type": "divider"})

    blocks.append(create_slack_values_block(payload))
    blocks.append({
        "type": "divider",
    })

    buttons = []

    link = payload.get("link", None)
    if link is not None:
        buttons.append({
            "type": "button",
            "text": {
                    "type": "plain_text",
                    "text": "View Root Cause",
                    "emoji": True,
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action",
        })

    if buttons:
        blocks.append({
            "type": "actions",
            "elements": buttons,
        })

    return blocks


def create_slack_cleared_payload(payload):
    blocks = [
        {
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "emoji",
                    "name": "white_check_mark",
                }],
            }],
        }, {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Root Cause {payload.get('name')} cleared",
            },
        },
    ]

    desc_block = create_slack_description_block(payload)
    if desc_block is not None:
        blocks.append(desc_block)
        blocks.append({
            "type": "divider",
        })

    blocks.append(create_slack_values_block(payload))
    blocks.append({
        "type": "divider",
    })

    buttons = []

    link = payload.get("link", None)
    if link is not None:
        buttons.append({
            "type": "button",
            "text": {
                    "type": "plain_text",
                    "text": "View Root Cause",
                    "emoji": True,
            },
            "value": "click_me_123",
            "url": link,
            "action_id": "button-action",
        })

        blocks.append({
            "type": "actions",
            "elements": buttons,
        })

    return blocks


def forward_to_slack(payload, slack_webhook_url, slack_webhook_token):
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

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {slack_webhook_token}',
    }
    return requests.post(slack_webhook_url, json=slack_data, headers=headers)
