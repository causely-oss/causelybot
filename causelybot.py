from flask import Flask, request, jsonify
import requests
import os
import json
import yaml

app = Flask(__name__)

def load_config():
    with open("/etc/causelybot/config.yaml", 'r') as stream:
        return yaml.safe_load(stream)

config = load_config()

def filter_notification(payload):
    payload_name = payload.get("name").lower()  # Normalize case
    payload_entity_type = payload.get("entityType").lower()  # Normalize case

    # If the config is not specified or the filter is not enabled, allow the payload
    if not config.get("filterconfig", {}).get("enabled", False):
        return True

    # Boolean to determine if the payload should be forwarded
    allow_payload=True

    # Get allowed types from config, ensuring they are lists
    allowed_names = config.get("filterconfig", {}).get("problemTypes", [])
    allowed_entity_types = config.get("filterconfig", {}).get("entityTypes", [])

    # Edge case: Ensure allowed_names and allowed_entity_types are lists
    if not isinstance(allowed_names, list):
        allowed_names = []
    if not isinstance(allowed_entity_types, list):
        allowed_entity_types = []

    # Normalize case for the allowed types
    allowed_names = [name.lower() for name in allowed_names]
    allowed_entity_types = [etype.lower() for etype in allowed_entity_types]

    # If the payload name is not in the allowed names, do not allow the payload
    if allowed_names and payload_name not in allowed_names:
        allow_payload = False

    # If the payload entity type is not in the allowed entity types, do not allow the payload
    if allowed_entity_types and payload_entity_type not in allowed_entity_types:
        allow_payload = False

    return allow_payload

# Environment variables (can be passed as Kubernetes secrets)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
EXPECTED_TOKEN = os.getenv("BEARER_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():
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
                return jsonify({"message": "Failed to forward to Slack"}), 500
        else:
            return jsonify({"message": "Payload filtered out"}), 200
    else:
        return jsonify({"message": "Unauthorized"}), 401

def forward_to_slack(payload):
    # Prettify the payload and send it to Slack
    pretty_payload = json.dumps(payload, indent=4)
    slack_data = {
        "username": "Causely Bot",
        "icon_emoji": ":causely:",
        "text": f"```{pretty_payload}```",
    }
    headers = {'Content-Type': 'application/json'}
    return requests.post(SLACK_WEBHOOK_URL, json=slack_data, headers=headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
