# causelybot

causelybot is a webhook service designed to receive and authenticate incoming payloads, process them, and forward the relevant information to external systems such as Slack. This server-side application validates bearer tokens included in the payload, ensuring secure communication. Once authenticated, the bot forwards the payload to a specified Slack channel using a pre-configured Slack webhook URL, enabling streamlined notifications and updates.

## Causely Webhook endpoint configuration

Let's say we deploy our causelybot in a namespace `foo` then while installing the our causely agents we can configure the webhook endpoint as follows in the `values.yaml`:

```yaml
notifications:
  webhook:
    url: "http://causelybot.foo:5000/webhook/jira"    # Replace with your webhook URL
    token: "your-secret-token"                        # Replace with your webhook token
    enabled: true
```

or

```yaml
notifications:
  webhook:
    url: "http://causelybot.foo:5000/webhook/opsgenie" # Replace with your webhook URL
    token: "your-secret-token"                         # Replace with your webhook token
    enabled: true
```

or

```yaml
notifications:
  webhook:
    url: "http://causelybot.foo:5000/webhook/slack"    # Replace with your webhook URL
    token: "your-secret-token"                         # Replace with your webhook token
    enabled: true

```

or

```yaml
notifications:
  webhook:
    url: "http://causelybot.foo:5000/webhook/teams"    # Replace with your webhook URL
    token: "your-secret-token"                         # Replace with your webhook token
    enabled: true
```

The executor also needs to be enabled and deployed with our causely agents. This can be done by enabling it in the `values.yaml` as follows:

```yaml
executor:
  enabled: true
```

The causelybot will just forward the incoming payload to another endpoint. The example below is shown on Slack but it can be configured for Discord, PagerDuty etc.

## Usage

### Clone the repository

```shell
git clone git@github.com:causely-oss/causelybot.git
cd causelybot
```

### Docker Build

Build the Docker image for our causelybot as follows:

```shell
docker buildx build -t us-docker.pkg.dev/public-causely/public/bot --platform linux/amd64,linux/arm64 --push .
```

### Helm Install

```shell
helm install bot ./helm/causelybot --namespace foo --set webhooks[0].url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX" --set auth.token="your-secret-token" --set image.repository="<repository>" --set image.tag="<tag>"
```

## Notification Payload

Below is an example of what the raw payload looks as:

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

Below is an example of what a problem detected notification looks like in slack:

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

## Filtering Notifications

### Field Registery

Filtering notifications can be done based on pre-defined fields or custom defined fields in [FIELD_DEFINITIONS](causely_notification/field_registry.py). Few examples of fields definitions are shown below:

```json
{
    "severity": {"type": "direct", "path": "severity"},
    "entity.type": {"type": "direct", "path": "entity.type"},
    "impactsSLO": {"type": "computed", "func": "compute_impact_slo"},
}
```

We have defined the fields on which we want to do the filtering. There are two types of fields: `direct` and `computed`:

- Direct field means that the value of field can be parsed by following a path in nested dictionary. For example in the raw payload you have entity as the key and value is a dict containing more information and if we want to retrieve type then we provide the fully path with a dot notation as shown above.
- Computed field means that some computation must be done on the payload to get the value of that field. Refer to the the example `impactsSLO` which we use to decide if a payload consisted of any impacted SLOs and use that as a filter.

### Filter Operators

We have provided support for certain operators to do the comparison between `operand1` and `operand2` for filtering:

- `equals`: This is used to compare whether a specific field in a payload matches the given value:

```yaml
webhooks:
  - name: "slack-malfunction"
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
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
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
    filters:
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
```

We also support the inverse-operations like `not_equals` and `not_in` as well. You can also provide multiple filters for a webhook like:

```yaml
webhooks:
  - name: "slack-malfunction-slo"
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
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

## Multiple Webhooks

We also support providing multiple webhooks each with their own sets of filters:

```yaml
webhooks:
  - name: "slack-malfunction-slo"
    url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
    filters:
      enabled: true
      values:
        - field: "name"
          operator: "equals"
          value: "Malfunction"
        - field: "impactsSLO"
          operator: "equals"
          value: True
  - name: "slack-severity"
    url: "https://hooks.slack.com/services/T00000000/B00000001/XXXXXXXXXXXXXXXXXXXXXXXX"
    token: ""
    filters:
      enabled: true
      values:
        - field: "severity"
          operator: "in"
          value: ["High", "Critical"]
```
