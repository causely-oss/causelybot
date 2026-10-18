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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from .utils import check_problem_detected

SCOPE_NAME = "causely.notification"

SEVERITY_MAP = {
    "Low": (9, "INFO"),
    "Medium": (13, "WARN"),
    "High": (17, "ERROR"),
    "Critical": (21, "FATAL"),
}

CLEARED_SEVERITY = (9, "INFO")

# Labels copied to resource attributes for correlation with existing telemetry.
RESOURCE_LABEL_KEYS = (
    "k8s.cluster.name",
    "k8s.namespace.name",
    "k8s.cluster.uid",
    "k8s.controller.kind",
    "causely.ai/cluster",
    "causely.ai/namespace",
)


def build_logs_url(base_url: str) -> str:
    """Append /v1/logs to the OTLP HTTP base URL."""
    return f"{base_url.rstrip('/')}/v1/logs"


def timestamp_to_nanos(iso_date_str: Optional[str]) -> str:
    if iso_date_str is None:
        return str(int(datetime.now(timezone.utc).timestamp() * 1_000_000_000))
    normalized = iso_date_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return str(int(dt.timestamp() * 1_000_000_000))


def _severity_for_payload(payload: Dict[str, Any], is_detected: bool) -> Tuple[int, str]:
    if not is_detected:
        return CLEARED_SEVERITY
    return SEVERITY_MAP.get(payload.get("severity", ""), (13, "WARN"))


def _string_attr(key: str, value: str) -> Dict[str, Any]:
    return {"key": key, "value": {"stringValue": value}}


def _build_log_body(payload: Dict[str, Any], is_detected: bool) -> str:
    name = payload.get("name", "Unknown")
    entity_name = payload.get("entity", {}).get("name", "Unknown Entity")
    severity = payload.get("severity", "Unknown")
    if is_detected:
        return f"Root cause identified: {name} on {entity_name} ({severity})"
    return f"Root cause cleared: {name} on {entity_name} ({severity})"


def _build_resource_attributes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    attrs: List[Dict[str, Any]] = []

    entity = payload.get("entity", {})
    entity_name = entity.get("name")
    service_name = entity_name or "causely"
    attrs.append(_string_attr("service.name", service_name))

    if entity_name:
        attrs.append(_string_attr("causely.entity.name", entity_name))

    entity_type = entity.get("type")
    if entity_type:
        attrs.append(_string_attr("causely.entity.type", entity_type))

    entity_id = entity.get("id")
    if entity_id:
        attrs.append(_string_attr("causely.entity.id", entity_id))

    labels = payload.get("labels", {})
    if isinstance(labels, dict):
        for key in RESOURCE_LABEL_KEYS:
            value = labels.get(key)
            if value is not None:
                attrs.append(_string_attr(key, str(value)))

    return attrs


def _build_log_attributes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    attrs: List[Dict[str, Any]] = []

    def add(key: str, value: Any) -> None:
        if value is not None and value != "":
            attrs.append(_string_attr(key, str(value)))

    add("causely.type", payload.get("type"))
    add("causely.name", payload.get("name"))
    add("causely.severity", payload.get("severity"))
    add("causely.object_id", payload.get("objectId"))
    add("causely.link", payload.get("link"))
    add("causely.object_type", payload.get("object_type"))

    entity = payload.get("entity", {})
    add("causely.entity.id", entity.get("id"))
    add("causely.entity.name", entity.get("name"))
    add("causely.entity.type", entity.get("type"))
    add("causely.entity.link", entity.get("link"))

    description = payload.get("description", {})
    if isinstance(description, dict):
        add("causely.summary", description.get("summary"))
        add("causely.details", description.get("details"))

        remediation = description.get("remediationOptions", [])
        if remediation:
            attrs.append(_string_attr("causely.remediation", json.dumps(remediation)))

    labels = payload.get("labels", {})
    if isinstance(labels, dict):
        for key, value in labels.items():
            add(f"causely.labels.{key}", value)

    slos = payload.get("slos")
    if slos:
        attrs.append(_string_attr("causely.slos", json.dumps(slos)))

    duration_ns = payload.get("duration_ns")
    if duration_ns is not None:
        add("causely.duration_ns", duration_ns)

    attrs.append(_string_attr("causely.payload", json.dumps(payload)))
    return attrs


def create_otlp_logs_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    is_detected = check_problem_detected(payload)
    severity_number, severity_text = _severity_for_payload(payload, is_detected)

    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": _build_resource_attributes(payload),
                },
                "scopeLogs": [
                    {
                        "scope": {"name": SCOPE_NAME},
                        "logRecords": [
                            {
                                "timeUnixNano": timestamp_to_nanos(payload.get("timestamp")),
                                "severityNumber": severity_number,
                                "severityText": severity_text,
                                "body": {"stringValue": _build_log_body(payload, is_detected)},
                                "attributes": _build_log_attributes(payload),
                            }
                        ],
                    }
                ],
            }
        ]
    }


def forward_to_otlp(payload: Dict[str, Any], base_url: str, token: str = None):
    print(payload, file=sys.stderr)
    print(payload.get("type"), file=sys.stderr)

    url = build_logs_url(base_url)
    otlp_data = create_otlp_logs_payload(payload)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(url, json=otlp_data, headers=headers)

    if response.status_code not in [200, 201, 202]:
        print(f"Error posting to OTLP endpoint: {response.status_code}, {response.text}", file=sys.stderr)
    else:
        print("Payload successfully forwarded to OTLP endpoint.", file=sys.stderr)

    return response
