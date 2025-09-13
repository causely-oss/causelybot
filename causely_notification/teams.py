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
from .utils import check_problem_detected


def create_teams_description_block(payload):
    summary = payload.get("description", {}).get("summary", None)
    if summary is None:
        return None

    return {
        "type": "TextBlock",
        "text": f"**Summary:**\n{summary}",
        "wrap": True
    }


def create_teams_remediation_option_block(payload):
    ro = payload.get("description", {}).get("remediationOptions", [])
    if len(ro) == 0:
        return None

    blocks = [{
        "type": "TextBlock",
        "text": f"**Remediation: {ro[0].get('title')}**\n{ro[0].get('description')}",
        "wrap": True
    }]

    link = payload.get("link", None)
    if len(ro) > 1 and link is not None:
        blocks.append({
            "type": "Action.OpenUrl",
            "title": "View More",
            "url": link
        })

    return blocks


def create_teams_slo_blocks(payload):
    slos = payload.get("slos", [])
    if not slos:
        return None

    blocks = [{
        "type": "TextBlock",
        "text": "**Impacted SLOs**",
        "weight": "bolder",
        "size": "large"
    }]

    for slo in slos:
        slo_entity = slo.get("slo_entity", {})
        slo_name = slo_entity.get("name", "Unknown SLO")
        slo_link = slo_entity.get("link")
        slo_status = slo.get("status", "UNKNOWN")

        related_entity = slo.get("related_entity", {})
        related_entity_name = related_entity.get("name", "Unknown Service")
        related_entity_link = related_entity.get("link")
        related_entity_text = f"[{related_entity_name}]({related_entity_link})" if related_entity_link else related_entity_name

        # Status icons and text
        status_icons = {
            "AT_RISK": "⚠️",
            "HEALTHY": "✅",
            "VIOLATED": "❌",
            "NORMAL": "❓",
            "UNKNOWN": "❓"
        }
        status_icon = status_icons.get(slo_status, "❓")
        status_text = slo_status.replace("_", " ").title()

        slo_text = f"{status_icon} **{slo_name}** ({status_text})\n- **Impacted Service:** {related_entity_text}"
        if slo_link:
            slo_text = f"{status_icon} [{slo_name}]({slo_link}) ({status_text})\n- **Impacted Service:** {related_entity_text}"

        blocks.append({
            "type": "TextBlock",
            "text": slo_text,
            "wrap": True
        })

    return blocks


def create_teams_values_block(payload):
    entity = payload.get("entity", {})
    entity_name = entity.get("name", "Unknown Entity")
    entity_link = entity.get("link")
    entity_text = f"[{entity_name}]({entity_link})" if entity_link else entity_name

    # Extract cluster and namespace information from labels
    labels = payload.get("labels", {})
    cluster_name = labels.get("k8s.cluster.name", "Unknown Cluster")
    namespace_name = labels.get("k8s.namespace.name", "Unknown Namespace")

    return {
        "type": "TextBlock",
        "text": (
            f"- **Affected Entity:** {entity_text}\r- **Cluster:** {cluster_name}\r- **Namespace:** {namespace_name}\r- **Severity:** {payload.get('severity')}\r- **Identified At:** {parse_iso_date(payload.get('timestamp'))}"
        ),
        "wrap": True
    }


def create_teams_detected_payload(payload):
    body = [
        {
            "type": "TextBlock",
            "text": f"⚠️ **Root Cause Identified: {payload.get('name')}**",
            "weight": "bolder",
            "size": "large",
            "wrap": True
        },
        {
            "type": "TextBlock",
            "text": "---"
        },
        create_teams_values_block(payload),
        {
            "type": "TextBlock",
            "text": "---"
        }
    ]

    desc_block = create_teams_description_block(payload)
    if desc_block is not None:
        body.append(desc_block)
        body.append({
            "type": "TextBlock",
            "text": "---"
        })

    rem_blocks = create_teams_remediation_option_block(payload)
    if rem_blocks is not None:
        body.extend(rem_blocks)
        body.append({
            "type": "TextBlock",
            "text": "---"
        })

    slo_blocks = create_teams_slo_blocks(payload)
    if slo_blocks is not None:
        body.extend(slo_blocks)
        body.append({
            "type": "TextBlock",
            "text": "---"
        })

    action_block = []
    link = payload.get("link", None)
    if link is not None:
        action_block.append({
            "type": "Action.OpenUrl",
            "title": "View Root Cause",
            "url": link
        })

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "body": body,
                "actions": action_block,
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.2"
            }
        }]
    }


def create_teams_cleared_payload(payload):
    body = [
        {
            "type": "TextBlock",
            "text": f"✅ **Root Cause Cleared: {payload.get('name')}**",
            "weight": "bolder",
            "size": "large"
        },
        {
            "type": "TextBlock",
            "text": "---"
        },
        create_teams_values_block(payload),
        {
            "type": "TextBlock",
            "text": "---"
        }
    ]

    desc_block = create_teams_description_block(payload)
    if desc_block is not None:
        body.append(desc_block)
        body.append({
            "type": "TextBlock",
            "text": "---"
        })

    action_block = []
    link = payload.get("link", None)
    if link is not None:
        action_block.append({
            "type": "Action.OpenUrl",
            "title": "View Root Cause",
            "url": link
        })

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "body": body,
                "actions": action_block,
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.2"
            }
        }]
    }

def make_error_response(status_code: int, message: str) -> requests.Response:
    """
    Create a synthetic requests.Response object with a given status code and message.
    Useful for returning a consistent error response when HTTP calls fail.
    """
    resp = requests.Response()
    resp.status_code = status_code
    resp._content = message.encode("utf-8")
    resp.reason = message  # optional, sets a short description
    resp.url = ""  # optional: can set to the original request URL
    return resp


def forward_to_teams(payload, teams_webhook_url):
    # Validate webhook URL
    if not teams_webhook_url:
        print("ERROR: Teams webhook URL is not configured", file=sys.stderr)
        return make_error_response(500, "Teams webhook URL not configured".encode('utf-8'))

    # Prettify the payload and send it to Teams
    print(f"Processing Teams webhook for payload type: {payload.get('type')}", file=sys.stderr)
    print(f"Teams webhook URL: {teams_webhook_url}", file=sys.stderr)

    if check_problem_detected(payload):
        teams_data = create_teams_detected_payload(payload)
    else:
        teams_data = create_teams_cleared_payload(payload)

    print(f"Teams message data: {json.dumps(teams_data, indent=2)}", file=sys.stderr)

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        print(f"Sending request to Teams webhook...", file=sys.stderr)
        response = requests.post(teams_webhook_url, json=teams_data, headers=headers, timeout=30)
        print(f"Teams webhook response status: {response.status_code}", file=sys.stderr)
        print(f"Teams webhook response content: {response.content}", file=sys.stderr)

        if response.status_code in [200, 202]:
            print("Teams webhook request successful", file=sys.stderr)
        else:
            print(f"Teams webhook failed with status {response.status_code}: {response.text}", file=sys.stderr)

        return response
    except requests.exceptions.Timeout:
        error_msg = "Teams webhook request timed out after 30 seconds"
        print(error_msg, file=sys.stderr)
        return make_error_response(500, f"Request failed: {str(e)}".encode('utf-8'))
    except requests.exceptions.RequestException as e:
        print(f"Exception occurred while sending to Teams webhook: {e}", file=sys.stderr)
        return make_error_response(500, f"Request failed: {str(e)}".encode('utf-8'))
