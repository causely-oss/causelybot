# Causelybot
causelybot is a webhook service designed to receive and authenticate incoming payloads, process them, and forward the relevant information to external systems such as Slack. This server-side application validates bearer tokens included in the payload, ensuring secure communication. Once authenticated, the bot forwards the payload to a specified Slack channel using a pre-configured Slack webhook URL, enabling streamlined notifications and updates.

## Causely Webhook endpoint configuration

Let's say we deploy our causelybot in a namespace `foo` then while installing the our causely agents we can configure the webhook endpoint as follows in the `values.yaml`:

```yaml
notifications:
  webhook:
    url: "http://causelybot.foo:5000/webhook"   # Replace with your webhook URL
    token: "your-secret-token"                  # Replace with your webhook token
    enabled: true
```

The causely bot will just forward the incoming payload to another endpoint. The example below is shown on Slack but it can be configured for Discord, PagerDuty e.t.c. 

## Usage

### Clone the directory

```shell
git clone git@github.com:Causely/causelybot.git
cd causelybot
```

### Docker Build
Build the Docker image for our causelybot as follows:

```shell
docker build -t <repository>:<tag> .
docker push <repository>:<tag>
```

### Helm Install

```shell
helm install bot ./helm/causelybot --namespace foo --set webhook.url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX" --set webhook.token="your-secret-token" --set image.repository="<repository>"
```

## Notification Payload

Below is an example of the notification payload in slack:

![Slack Example](assets/slack.png "Slack Example")

Payload fields:

- `name`: The event name, in this case it's the defect name.
- `type`: The type of notification.
- `entityName`: The name of the entity that the notification is about.
- `entityType`: The type of entity.
- `description`: A description of the issue.
- `timestamp`: The timestamp when the issue was detected.
- `labels`: Metadata or tags that provide additional context (e.g., app name, Kubernetes namespace, and cluster information).
- `entityId`: The unique identifier for the entity involved.
- `objectId`: A unique identifier for the specific object associated with this event, in this case it's the defectID.

## Filtering Notifications
A very simple filter configuration has been provided to filter notifications based on `problemType` and `entityType`. This can be set by customizing the `filterconfig` map as seen below:

```yaml
filterConfig:
  enabled: false
  filters:
    - problemType: "Malfunction"
      entityType: "Pod"
```
Set the `enabled` flag to true to enable filtering and add the respective pairs of problemTypes and entityTypes for which you want to receive the notifications. If you want to allow notifications for only single filter then set the other to an empty string, for example:

```yaml
filterConfig:
  enabled: true
  filters:
    - problemType: ""
      entityType: "KubernetesService"
```
will allow all problem notifications for KubernetesService.