from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# Environment variables (can be passed as Kubernetes secrets)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
EXPECTED_TOKEN = os.getenv("BEARER_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Forward the payload to Slack
        response = forward_to_slack(payload)
        if response.status_code == 200:
            return jsonify({"message": "Payload forwarded to Slack"}), 200
        else:
            return jsonify({"message": "Failed to forward to Slack"}), 500
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
