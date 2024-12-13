{{/*
Validate required fields in values.yaml
*/}}
{{- define "validateAuthToken" -}}
  {{- if not .Values.auth.token -}}
    {{- fail "Error: 'auth.token' must be provided in values.yaml or via --set." -}}
  {{- end -}}
{{- end -}}
{{- define "validateWebhooks" -}}
  {{- if not .Values.webhooks -}}
    {{- fail "Error: 'webhooks' must be provided in values.yaml or via --set." -}}
  {{- end -}}
  {{- range .Values.webhooks }}
    {{- if not .name -}}
      {{- fail "Error: 'name' must be provided for each webhook in values.yaml or via --set." -}}
    {{- end -}}
    {{- if not .url -}}
      {{- fail (printf "Error: 'url' must be provided for webhook '%s' in values.yaml or via --set." .name) -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

{{- define "validateImageRepository" -}}
  {{- if not .Values.image.repository -}}
    {{- fail "Error: 'image.repository' must be provided in values.yaml or via --set." -}}
  {{- end -}}
{{- end -}}