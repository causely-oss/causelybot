# CauselyBot

CauselyBot is a webhook service designed to receive and authenticate incoming payloads, process them, and forward the relevant information to external systems such as Slack, Teams, Jira, and OpsGenie. This server-side application validates bearer tokens included in the payload, ensuring secure communication. Once authenticated, the bot forwards the payload to specified channels using pre-configured webhook URLs, enabling streamlined notifications and updates.

## Overview

To get up and running with CauselyBot, follow these steps:

1. **Configure CauselyBot** - Set up your webhook configurations, authentication token, and filtering rules
2. **Deploy CauselyBot** - Install and deploy the service using Docker or Helm
3. **Configure Causely** - Update your Causely instance to send notifications to CauselyBot
4. **Test CauselyBot** - Confirm your CauselyBot sends alerts to your webhook endpoints

See the sections below for detailed configuration and deployment instructions.

## 1. CauselyBot Configuration

### Clone the repository

```shell
git clone https://github.com/causely-oss/causelybot.git
```

CauselyBot Docker images are pre-built and published to `us-docker.pkg.dev/public-causely/public/bot:latest`. See Appendix section for building image locally.

### Configure Webhook

Create a `causelybot-values.yaml` file with your configuration. Use the example below and update the following fields:

- `<YOUR_CAUSELYBOT_TOKEN>` [Required] Define your CauselyBot token here. This will be referenced in the Causely configuration `causely-values.yaml`
- `<FRIENDLY_WEBHOOK_NAME>` [Required] Unique name for your webhook
- `<YOUR_WEBHOOK_TYPE>` [Required] Set to one of the following: `slack`, `teams`, `jira`, `opsgenie`
- `<YOUR_WEBHOOK_URL>` [Required] The URL of your webhook endpoint
- `<YOUR_WEBHOOK_TOKEN>` [Optional] If required by your webhook, provide a token

```yaml
auth:
  token: "<YOUR_CAUSELYBOT_TOKEN>" # Required - define your token here and then use in the Causely configuration (causely-values.yaml)

webhooks:
  - name: "<FRIENDLY_WEBHOOK_NAME>" # Required
    hook_type: "<YOUR_WEBHOOK_TYPE>" # Required [slack, teams, jira, opsgenie]
    url: "<YOUR_WEBHOOK_URL>" # Required
    token: "<YOUR_WEBHOOK_TOKEN>" # Optional
    filters: # Optional - see Filtering Notifications
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
```

## 2. Deploy Causelybot

Install via Helm using the `causelybot-values.yaml` file:

```shell
helm upgrade --install causelybot ./causelybot/helm/causelybot --namespace causelybot --values causelybot-values.yaml
```

## 3. Configure Causely

To configure Causely to send notifications to CauselyBot, you must enable the `executor` and specify the CauselyBot endpoint. Add the following entries to your `causely-values.yaml` file:

```yaml
executor:
  enabled: true

notifications:
  webhook:
    url: "http://<CAUSELYBOT_FQDN/IP>:5000/webhook"
    token: "<YOUR_CAUSELYBOT_TOKEN>"
    enabled: true
```

**Important Notes:**

- Replace `<CAUSELYBOT_FQDN/IP>` with the actual FQDN or IP address where CauselyBot is deployed. If deployed within the same cluster in the causelybot namespace, use:<br>
  `causelybot.causelybot.svc.cluster.local.`
- Replace `<YOUR_CAUSELYBOT_TOKEN>` with the same token you configured in CauselyBot (see configuration section above)
- See [Causely's Documentation](https://docs.causely.ai/installation/customize/) for additional details on `causely-values.yaml` usage

Apply the changes to Causely:

```bash
helm upgrade --install causely --create-namespace oci://us-docker.pkg.dev/public-causely/public/causely --version <version> --namespace=causely --values </path/to/causely-values.yaml>
```

## 4. Test CauselyBot

1. To confirm your webhook has been configured correctly, in Causely, navigate to Gear Icon > Integrations > [Webhooks](https://portal.causely.app/integrations?tab=webhooks)
2. Click "Send Test Notification" to trigger a test payload.
3. If the configuration is working, a test payload will be sent from the Executor to CauselyBot to your wehbook endpoint(s). If you do not receive the test notification, you can check the logs of the executor and causelybot for more details:
   - `kubectl logs -f deploy/executor -n causely`
   - `kubectl logs -f deploy/causelybot -n causelybot`

## Appendix

### Notification Payload

Below is an example of the raw payload sent from the Executor to CauselyBot:

```json
{
  "link": "http://causely.localhost:3000/rootCauses/81703742-b81a-43b0-8509-1e9ac718e2e3",
  "name": "Malfunction",
  "slos": [
    {
      "status": "AT_RISK",
      "slo_entity": {
        "id": "988a33f8-afea-5b3b-b7e7-a578fe5184f1",
        "link": "http://causely.localhost:3000/topology/988a33f8-afea-5b3b-b7e7-a578fe5184f1",
        "name": "istio-system/prometheus-RequestSuccessRate",
        "type": "RatioSLO"
      },
      "related_entity": {
        "id": "6abdca4f-9574-42ec-a6c4-c4ba34f11c92",
        "link": "http://causely.localhost:3000/topology/6abdca4f-9574-42ec-a6c4-c4ba34f11c92",
        "name": "istio-system/prometheus",
        "type": "KubernetesService"
      }
    }
  ],
  "type": "ProblemDetected",
  "entity": {
    "id": "030fdbc4-8d3b-58f7-aa51-259b75374174",
    "link": "http://causely.localhost:3000/topology/030fdbc4-8d3b-58f7-aa51-259b75374174",
    "name": "istio-system/prometheus-7f467df8b6-zhmqc",
    "type": "ApplicationInstance"
  },
  "labels": {
    "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
    "k8s.cluster.name": "dev",
    "k8s.namespace.name": "istio-system"
  },
  "objectId": "81703742-b81a-43b0-8509-1e9ac718e2e3",
  "severity": "High",
  "timestamp": "2024-12-13T06:43:08.309296138Z",
  "description": {
    "summary": "An application is experiencing a high rate of errors, causing disruptions for clients. This can lead to degraded performance, failed requests, or complete service unavailability, significantly affecting the user experience.",
    "remediationOptions": [
      {
        "title": "Check Logs",
        "description": "Inspect the container logs for error messages or stack traces, which can provide clues about the issue.\n"
      }
    ]
  }
}
```

Below is an example of what a root cause notification looks like in Slack:

![Slack Example](assets/slack_detect_notification.png "Slack Example")

Payload fields:

- `name`: The event name, in this case it's the problem name.
- `type`: The type of notification (e.g., "ProblemDetected").
- `entity`: The details regarding the entity for which the notification is triggered:
  - `id`: Id of the entity
  - `name`: Name of the entity
  - `type`: Type of the entity
- `description`: A description of the issue.
- `timestamp`: The timestamp when the issue was detected.
- `labels`: Metadata or tags that provide additional context (e.g., app name, Kubernetes namespace, and cluster information).
- `objectId`: A unique identifier for the specific object associated with this event, in this case it's the problem Id.
- `severity`: This is the severity of the problem detected/cleared.
- `slos`: If this field exists then it lists the impacted SLOs.

### Filtering Notifications

#### Field Registery

Filtering notifications can be done based on pre-defined fields or custom defined fields in [FIELD_DEFINITIONS](causely_notification/field_registry.py). A few examples of fields definitions are shown below:

```json
{
    "severity": {"type": "direct", "path": "severity"},
    "entity.type": {"type": "direct", "path": "entity.type"},
    "impactsSLO": {"type": "computed", "func": "compute_impact_slo"},
}
```

The fields on which filtering can be done are defined in the field registry. There are two types of fields: `direct` and `computed`:

- Direct field means that the value of field can be parsed by following a path in nested dictionary. For example in the raw payload you have entity as the key and value is a dict containing more information and if you want to retrieve type then you provide the full path with a dot notation as shown above.
- Computed field means that some computation must be done on the payload to get the value of that field. Refer to the example `impactsSLO` which is used to decide if a payload consisted of any impacted SLOs and use that as a filter.

#### Filter Operators

CauselyBot provides support for certain operators to do the comparison between `operand1` and `operand2` for filtering:

- `equals`: This is used to compare whether a specific field in a payload matches the given value:

```yaml
webhooks:
  - name: "slack-malfunction"
    hook_type: "slack"
    filters:
      enabled: true
      values:
        - field: "name"
          operator: "equals"
          value: "Malfunction"
```

- `in`: This is used to check whether a specific field in a payload is present in the given set:

```yaml
webhooks:
  - name: "slack-severity"
    hook_type: "slack"
    filters:
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
```

CauselyBot also supports inverse operations like `not_equals` and `not_in`. Multiple filters can be provided for a webhook like:

```yaml
webhooks:
  - name: "slack-malfunction-slo"
    hook_type: "slack"
    filters:
      enabled: true
      values:
        - field: "name"
          operator: "equals"
          value: "Malfunction"
        - field: "impactsSLO"
          operator: "equals"
          value: True
```

### Multiple Webhooks

CauselyBot also supports providing multiple webhooks each with their own sets of filters:

```yaml
webhooks:
  - name: "slack-malfunction-slo"
    hook_type: "slack"
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: "xoxb-1234567890-1234567890-XXXXXXXXXXXXXXXXXXXXXXXX"
    filters:
      enabled: true
      values:
        - field: "name"
          operator: "equals"
          value: "Malfunction"
        - field: "impactsSLO"
          operator: "equals"
          value: True
  - name: "jira-critical-tickets"
    hook_type: "jira"
    url: "https://your-domain.atlassian.net/rest/api/3/issue"
    token: "your-jira-token"
    filters:
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
  - name: "teams-all-notifications"
    hook_type: "teams"
    url: "https://your-domain.webhook.office.com/webhookb2/..."
    filters:
      enabled: false # No filtering - receives all notifications
```

### Docker Image

CauselyBot Docker images are pre-built and published to:

```text
us-docker.pkg.dev/public-causely/public/bot:latest
```

If you need to build the image locally for development or custom modifications:

```shell
docker buildx build -t us-docker.pkg.dev/public-causely/public/bot --platform linux/amd64,linux/arm64 --push .
```
