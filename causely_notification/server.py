from __future__ import annotations

import os
import sys

import yaml
from flask import Flask
from flask import jsonify
from flask import request

from causely_notification.filter import WebhookFilterStore
from causely_notification.jira import forward_to_jira
from causely_notification.slack import forward_to_slack
from causely_notification.teams import forward_to_teams

app = Flask(__name__)


def load_config():
    with open("/etc/causelybot/config.yaml", 'r') as stream:
        return yaml.safe_load(stream)


def get_config():
    return load_config()


EXPECTED_TOKEN = os.getenv("AUTH_TOKEN")

@app.route('/webhook/jira', methods=['POST'])
def webhook_jira():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        matching_webhooks = filter_store.filter_payload(payload)
        # If there are no matching webhooks, return 200 OK
        if not matching_webhooks:
            return jsonify({"message": "No matching webhooks found"}), 200
        # Forward the payload to all matching webhooks
        for name in matching_webhooks:
            jira_url = webhook_lookup_map[name]['url']
            jira_token = webhook_lookup_map[name]['token']
            response = forward_to_jira(payload, jira_url, jira_token)
            if response.status_code in (200, 201):  # Jira returns 201 for created issues
                return jsonify({"message": "Payload forwarded to Jira"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Jira"}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401

@app.route('/webhook/opsgenie', methods=['POST'])
def webhook_opsgenie():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        matching_webhooks = filter_store.filter_payload(payload)
        # If there are no matching webhooks, return 200 OK
        if not matching_webhooks:
            return jsonify({"message": "No matching webhooks found"}), 200
        # Forward the payload to all matching webhooks
        for name in matching_webhooks:
            opsgenie_url = webhook_lookup_map[name]['url']
            opsgenie_token = webhook_lookup_map[name]['token']
            response = forward_to_opsgenie(payload, opsgenie_url, opsgenie_token)
            if response.status_code == 202:  # Opsgenie returns 202 for success
                return jsonify({"message": "Payload forwarded to Opsgenie"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Opsgenie"}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401

@app.route('/webhook/slack', methods=['POST'])
def webhook_slack():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        matching_webhooks = filter_store.filter_payload(payload)
        # If there are no matching webhooks, return 200 OK
        if not matching_webhooks:
            return jsonify({"message": "No matching webhooks found"}), 200
        # Forward the payload to all matching webhooks
        for name in matching_webhooks:
            # Forward the payload to Slack
            response = forward_to_slack(
                payload, webhook_lookup_map[name]['url'], webhook_lookup_map[name]['token'],
            )
            if response.status_code == 200:
                return jsonify({"message": "Payload forwarded to Slack"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Slack"}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401

@app.route('/webhook/teams', methods=['POST'])
def webhook_teams():
    # Check for Bearer token in Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.split(" ")[1] == EXPECTED_TOKEN:
        payload = request.json
        # Check if the payload passes the filter
        matching_webhooks = filter_store.filter_payload(payload)
        # If there are no matching webhooks, return 200 OK
        if not matching_webhooks:
            return jsonify({"message": "No matching webhooks found"}), 200
        # Forward the payload to all matching webhooks
        for name in matching_webhooks:
            teams_url = webhook_lookup_map[name]['url']
            response = forward_to_teams(payload, teams_url)
            if response.status_code == 200:
                return jsonify({"message": "Payload forwarded to Teams"}), 200
            else:
                print(response.content, file=sys.stderr)
                return jsonify({"message": "Failed to forward to Teams"}), 500
    else:
        return jsonify({"message": "Unauthorized"}), 401


if __name__ == '__main__':
    # Step 1: Read the configuration file
    config = get_config()
    webhooks = config.get("webhooks", [])
    if not webhooks:
        raise ValueError("No webhooks found in the config.")

    # Step 2: Initialize the webhook filter store
    filter_store = WebhookFilterStore()

    # Step 3: Map of webhook names to their (url, token) from environment variables
    webhook_lookup_map = {}

    for webhook in webhooks:
        # Extract the webhook name and normalize it for the environment variable lookup
        webhook_name = webhook.get("name")
        if not webhook_name:
            raise ValueError("Webhook name is required in the configuration.")

        # Normalize the webhook name for environment variable lookup (uppercase and spaces to underscores)
        normalized_name = webhook_name.upper().replace(" ", "_")

        # Fetch the URL and Token for the webhook from environment variables
        url_env_var = f"URL_{normalized_name}"
        token_env_var = f"TOKEN_{normalized_name}"

        url = os.getenv(url_env_var)
        token = os.getenv(token_env_var)

        if not url:
            raise ValueError(f"Missing environment variable '{
                             url_env_var
                             }' for webhook '{webhook_name}'")

        # Store the webhook URL and token in the lookup map
        webhook_lookup_map[webhook_name] = {
            'url': url,
            'token': token,
        }

        # Extract and add filters for the webhook (if enabled)
        filters = webhook.get("filters", {})
        enabled = filters.get("enabled", False)
        filter_values = filters.get("values", [])

        # Add the webhook filters to the filter store
        filter_store.add_webhook_filters(webhook_name, filter_values, enabled)

    # Start the application
    app.run(host='0.0.0.0', port=5000)
