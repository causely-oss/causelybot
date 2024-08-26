{{/*
Validate required fields in values.yaml
*/}}
{{- define "validateWebhookUrl" -}}
{{- if not .Values.webhook.url -}}
{{- fail "Error: 'webhook.url' must be provided in values.yaml or via --set." -}}
{{- end -}}
{{- end -}}

{{- define "validateBearerToken" -}}
{{- if not .Values.webhook.token -}}
{{- fail "Error: 'webhook.token' must be provided in values.yaml or via --set." -}}
{{- end -}}
{{- end -}}

{{- define "validateImageRepository" -}}
{{- if not .Values.image.repository -}}
{{- fail "Error: 'image.repository' must be provided in values.yaml or via --set." -}}
{{- end -}}
{{- end -}}
