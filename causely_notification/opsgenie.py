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


def create_opsgenie_description(payload):
    description = payload.get("description", {}).get("summary", "No summary provided.")
    return description


def create_opsgenie_remediation(payload):
    remediation_options = payload.get("description", {}).get("remediationOptions", [])
    if not remediation_options:
        return "No remediation options provided."
    return "\n".join(
        [f"- {option.get('title')}: {option.get('description')}" for option in remediation_options]
    )


def create_opsgenie_slos(payload):
    slos = payload.get("slos", [])
    if not slos:
        return "No SLOs impacted."

    status_icons = {
        "AT_RISK": "⚠️ At Risk",
        "HEALTHY": "✅ Healthy",
        "VIOLATED": "❌ Violated",
        "NORMAL": "ℹ️ Normal",
        "UNKNOWN": "❓ Unknown",
    }

    slo_lines = ["Impacted SLOs:"]
    for slo in slos:
        slo_entity = slo.get("slo_entity", {})
        slo_name = slo_entity.get("name", "Unknown SLO")
        slo_status = slo.get("status", "UNKNOWN")
        slo_status_text = status_icons.get(slo_status, slo_status)

        related_entity = slo.get("related_entity", {})
        related_entity_name = related_entity.get("name", "Unknown Service")

        slo_lines.append(f"- {slo_name} ({slo_status_text}) - Impacted Service: {related_entity_name}")

    return "\n".join(slo_lines)


def create_opsgenie_payload(payload, type_: str):
    entity = payload.get("entity", {})
    entity_name = entity.get("name", "Unknown Entity")
    timestamp = parse_iso_date(payload.get("timestamp"))
    severity = payload.get("severity", "Unknown")
    description = create_opsgenie_description(payload)
    remediation = create_opsgenie_remediation(payload)
    slos = create_opsgenie_slos(payload)

    message = f"{type_}: {payload.get('name', 'No name provided')}"
    details = {
        "severity": severity,
        "affected_entity": entity_name,
        "timestamp": timestamp,
        "description": description,
        "remediation": remediation,
        "slos": slos,
    }

    return {
        "message": message,
        "description": description,
        "details": details,
        "priority": severity.upper(),
    }


def forward_to_opsgenie(payload, opsgenie_api_url, opsgenie_api_key):
    print(payload, file=sys.stderr)
    print(payload.get("type"), file=sys.stderr)

    type_ = "Root Cause Identified" if check_problem_detected(payload) else "Root Cause Cleared"
    opsgenie_data = create_opsgenie_payload(payload, type_)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"GenieKey {opsgenie_api_key}",
    }

    response = requests.post(opsgenie_api_url, json=opsgenie_data, headers=headers)

    if response.status_code != 202:  # Opsgenie returns 202 for accepted requests
        print(f"Error posting to Opsgenie: {response.status_code}, {response.text}", file=sys.stderr)
    else:
        print("Payload successfully forwarded to Opsgenie.", file=sys.stderr)

    return response