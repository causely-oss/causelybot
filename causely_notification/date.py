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

from datetime import datetime


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
    except ValueError:
        return iso_date_str
