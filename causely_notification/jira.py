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


def create_jira_description(payload):
    description = payload.get("description", {}).get("summary", "No summary provided.")
    return description


def create_jira_remediation(payload):
    remediation_options = payload.get("description", {}).get("remediationOptions", [])
    if not remediation_options:
        return "No remediation options provided."
    return "\n".join(
        [f"* {option.get('title')}: {option.get('description')}" for option in remediation_options]
    )


def create_jira_slos(payload):
    slos = payload.get("slos", [])
    if not slos:
        return "No SLOs impacted."

    # Jira uses different status mappings
    status_icons = {
        "AT_RISK": "🔸 At Risk",
        "HEALTHY": "✅ Healthy",
        "VIOLATED": "🔴 Violated",
        "NORMAL": "ℹ️ Normal",
        "UNKNOWN": "❓ Unknown",
    }

    slo_lines = ["h2. Impacted SLOs\n"]  # Using Jira markup
    for slo in slos:
        slo_entity = slo.get("slo_entity", {})
        slo_name = slo_entity.get("name", "Unknown SLO")
        slo_status = slo.get("status", "UNKNOWN")
        slo_status_text = status_icons.get(slo_status, slo_status)

        related_entity = slo.get("related_entity", {})
        related_entity_name = related_entity.get("name", "Unknown Service")

        slo_lines.append(f"* {slo_name} ({slo_status_text}) - Impacted Service: {related_entity_name}")

    return "\n".join(slo_lines)


def create_jira_payload(payload, type_: str):
    entity = payload.get("entity", {})
    entity_name = entity.get("name", "Unknown Entity")
    timestamp = parse_iso_date(payload.get("timestamp"))
    severity = payload.get("severity", "Unknown")
    
    # Map severity to Jira priority levels
    priority_map = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "info": "Lowest",
    }
    
    jira_priority = priority_map.get(severity.lower(), "Medium")
    
    description = create_jira_description(payload)
    remediation = create_jira_remediation(payload)
    slos = create_jira_slos(payload)

    # Format description in Jira markup
    formatted_description = f"""h1. Incident Details
{description}

h2. Affected Entity
{entity_name}

h2. Severity
{severity}

h2. Timestamp
{timestamp}

h2. Remediation Steps
{remediation}

{slos}
"""

    return {
        "fields": {
            "project": {"key": "OPS"},  # This should be configurable
            "summary": f"{type_}: {payload.get('name', 'No name provided')}",
            "description": formatted_description,
            "issuetype": {"name": "Incident"},
            "priority": {"name": jira_priority},
            "labels": ["causely-alert"],
        }
    }


def forward_to_jira(payload, jira_api_url, jira_auth_token):
    print(payload, file=sys.stderr)
    print(payload.get("type"), file=sys.stderr)

    type_ = "Root Cause Identified" if check_problem_detected(payload) else "Root Cause Cleared"
    jira_data = create_jira_payload(payload, type_)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jira_auth_token}",
    }

    response = requests.post(f"{jira_api_url}/rest/api/2/issue", json=jira_data, headers=headers)

    if response.status_code not in (200, 201):  # Jira returns 201 for created issues
        print(f"Error creating Jira issue: {response.status_code}, {response.text}", file=sys.stderr)
    else:
        print("Issue successfully created in Jira.", file=sys.stderr)

    return response 