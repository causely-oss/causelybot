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
from typing import Any, Dict

import requests


class MockResponse:
    """Mock response object for debug webhook that doesn't make actual HTTP calls."""
    
    def __init__(self, status_code: int = 200, content: str = ""):
        self.status_code = status_code
        self.content = content


def forward_to_debug(payload: Dict[str, Any], url: str = None, token: str = None) -> MockResponse:
    """
    Debug webhook handler that prints payload information to stderr for development/testing.
    
    This webhook type is useful for local development and testing. It outputs formatted
    payload information without making any external HTTP calls, but shows what would
    be sent to the configured URL.
    
    Args:
        payload: The notification payload to process
        url: The webhook URL (shown in output but not called)
        token: The webhook token (length shown but value hidden)
        
    Returns:
        MockResponse object with status_code 200
    """
    print("\n" + "="*80, file=sys.stderr)
    print("🔍 DEBUG WEBHOOK - Notification Received", file=sys.stderr)
    print("="*80, file=sys.stderr)
    
    # Show URL and token info
    print(f"\n🌐 Target URL: {url}", file=sys.stderr)
    if token:
        token_length = len(token)
        print(f"🔑 Token: (present, length={token_length} chars)", file=sys.stderr)
    else:
        print(f"🔑 Token: (not provided)", file=sys.stderr)
    print(f"\n💬 Would send the following payload to the above URL:", file=sys.stderr)
    print("-"*80, file=sys.stderr)
    
    # Extract key information
    notification_type = payload.get("type", "Unknown")
    problem_name = payload.get("name", "Unknown")
    severity = payload.get("severity", "Unknown")
    timestamp = payload.get("timestamp", "Unknown")
    
    # Entity information
    entity = payload.get("entity", {})
    entity_name = entity.get("name", "Unknown")
    entity_type = entity.get("type", "Unknown")
    entity_id = entity.get("id", "Unknown")
    
    # Print summary
    print(f"📋 Type: {notification_type}", file=sys.stderr)
    print(f"📛 Name: {problem_name}", file=sys.stderr)
    print(f"⚠️  Severity: {severity}", file=sys.stderr)
    print(f"🕐 Timestamp: {timestamp}", file=sys.stderr)
    print(f"\n🎯 Entity:", file=sys.stderr)
    print(f"   - Name: {entity_name}", file=sys.stderr)
    print(f"   - Type: {entity_type}", file=sys.stderr)
    print(f"   - ID: {entity_id}", file=sys.stderr)
    
    # Description
    description = payload.get("description", {})
    summary = description.get("summary")
    if summary:
        print(f"\n📝 Summary:", file=sys.stderr)
        print(f"   {summary}", file=sys.stderr)
    
    # SLOs if present
    slos = payload.get("slos", [])
    if slos:
        print(f"\n📊 Impacted SLOs ({len(slos)}):", file=sys.stderr)
        for idx, slo in enumerate(slos, 1):
            slo_entity = slo.get("slo_entity", {})
            slo_name = slo_entity.get("name", "Unknown")
            slo_status = slo.get("status", "Unknown")
            print(f"   {idx}. {slo_name} - Status: {slo_status}", file=sys.stderr)
    
    # Labels
    labels = payload.get("labels", {})
    if labels:
        print(f"\n🏷️  Labels:", file=sys.stderr)
        for key, value in labels.items():
            print(f"   - {key}: {value}", file=sys.stderr)
    
    # Link
    link = payload.get("link")
    if link:
        print(f"\n🔗 Link: {link}", file=sys.stderr)
    
    # Full payload in JSON format
    print(f"\n📦 Full Payload (JSON):", file=sys.stderr)
    print(json.dumps(payload, indent=2), file=sys.stderr)
    
    print("="*80, file=sys.stderr)
    print("✅ Debug webhook processed successfully\n", file=sys.stderr)
    
    return MockResponse(status_code=200, content="Debug output printed to stderr")
