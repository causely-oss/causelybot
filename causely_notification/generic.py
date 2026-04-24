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

import sys
from typing import Any, Dict

import requests


def forward_to_generic(payload: Dict[str, Any], url: str, token: str = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code not in [200, 201, 202]:
        print(f"Error posting to generic webhook: {response.status_code}, {response.text}", file=sys.stderr)
    else:
        print("Payload successfully forwarded to generic webhook.", file=sys.stderr)
    return response
