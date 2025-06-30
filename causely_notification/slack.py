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

        related_entity = slo.get("related_entity", {})
        related_entity_name = related_entity.get("name", "Unknown Service")
        related_entity_link = related_entity.get("link")
        related_entity_text = f"<{related_entity_link}|{
            related_entity_name
        }>" if related_entity_link else related_entity_name

        # Icons for status with tooltip text (hover over icon)
        status_icons = {
            "AT_RISK": {"icon": ":warning:", "tooltip": "At Risk"},
            "HEALTHY": {"icon": ":white_check_mark:", "tooltip": "Healthy"},
            "VIOLATED": {"icon": ":x:", "tooltip": "Violated"},
            "NORMAL": {"icon": ":grey_question:", "tooltip": "Normal"},
            "UNKNOWN": {"icon": ":grey_question:", "tooltip": "Unknown"},
        }
        status_data = status_icons.get(
            slo_status, {"icon": ":grey_question:", "tooltip": slo_status},
        )

        # Construct the SLO text visually appealing with impacted service
        slo_text_lines = []
        icon_with_status = f"{status_data['icon']} *<{slo_link}|{slo_name}>* ({status_data['tooltip']})" if slo_link else f"{
            status_data['icon']
        } *{slo_name}* ({status_data['tooltip']})"
        slo_text_lines.append(icon_with_status)
        slo_text_lines.append(f"\t- *Impacted Service:* {related_entity_text}")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(slo_text_lines),
            },
        })

    return blocks


def create_slack_values_block(payload):
    entity = payload.get("entity", {})
    entity_name = entity.get("name", "Unknown Entity")
    entity_link = entity.get("link")
    entity_text = f"<{entity_link}|{
        entity_name
    }>" if entity_link else entity_name

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"*Severity:* {payload.get('severity')}\n"
                f"*Affected Entity:* {entity_text}\n"
                f"*Identified At:* {parse_iso_date(payload.get('timestamp'))}"
            ),
        },
    }


def create_slack_detected_payload(payload):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":exclamation: *Root Cause Identified: {payload.get('name')}*",
            },
        },
        {"type": "divider"},
        create_slack_values_block(payload),
        {"type": "divider"},
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
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: *Root Cause Cleared: {payload.get('name')}*",
            },
        },
        {"type": "divider"},
        create_slack_values_block(payload),
        {"type": "divider"},
    ]

    desc_block = create_slack_description_block(payload)
    if desc_block is not None:
        blocks.append(desc_block)
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
