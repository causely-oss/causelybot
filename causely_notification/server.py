import json
import os
import sys
from datetime import datetime

import requests
import yaml
from flask import Flask, jsonify, request

from causely_notification.slack import forward_to_slack

app = Flask(__name__)


def load_config():
    with open("/etc/causelybot/config.yaml", 'r') as stream:
        return yaml.safe_load(stream)


def get_config():
    return load_config()


def filter_notification(payload):
    # Load the config
    config = get_config()
    payload_name = payload.get("name").lower()  # Normalize case
    payload_entity_type = payload.get("entity", {}).get(
        "type", "").lower()  # Normalize case

    # If the config is not specified or the filter is not enabled, allow the payload
    if not config.get("filterconfig", {}).get("enabled", False):
        return True

    # Get filters from config
    filters = config.get("filterconfig", {}).get("filters", [])

    # Edge case: If filters are not specified correctly, allow all notifications
    if not isinstance(filters, list):
        return True

    # Check if the payload matches any of the filter pairs or partial matches
    for filter_pair in filters:
        allowed_name = filter_pair.get("problemType", "").lower()
        allowed_entity_type = filter_pair.get("entityType", "").lower()

        # Check for full match or partial matches
        if (allowed_name == payload_name or allowed_name == "") and \
           (allowed_entity_type == payload_entity_type or allowed_entity_type == ""):
            return True

    # If no matching filter pair is found, do not allow the payload
    return False


EXPECTED_TOKEN = os.getenv("BEARER_TOKEN")


@app.route('/webhook/slack', methods=['POST'])
def webhook_slack():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        if filter_notification(payload):
            # Forward the payload to Slack
            response = forward_to_slack(payload)
            if response.status_code == 200:
                return jsonify({"message": "Payload forwarded to Slack"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Slack"}), 500
        else:
            return jsonify({"message": "Payload filtered out"}), 200
    else:
        return jsonify({"message": "Unauthorized"}), 401


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
