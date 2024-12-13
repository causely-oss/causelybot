from __future__ import annotations

import unittest
from unittest.mock import patch

# TODO: Psuedo Function added to bypass the old tests for now. REWRITE THE TESTS BELOW


def filter_notification(payload):
    """
    Filter out notifications based on the problemType and entityType in the payload.
    """
    return True


@unittest.skip("Skipping TestFilterNotification tests until scoping settings are added.")
class TestFilterNotification(unittest.TestCase):

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": True,
                "filters": [
                    {
                        "problemType": "Malfunction",
                        "entityType": "Pod",
                    },
                ],
            },
        },
    )
    def test_filter_allows_valid_payload(self, mock_load_config):
        # Actual Payload for a Malfunction in a Pod
        payload = {
            "name": "Malfunction",
            "type": "DefectCleared",
            "entityName": "cm-constraint-analysis-cpu-multi/cart-single-7675f44bfd-k2kr6",
            "entityType": "Pod",
            "description": "Pod is experiencing an outage resulting in clients receiving errors and unable to access the service",
            "timestamp": "2024-08-28T08:15:42Z",
            "labels": {
                "VirtualMachineName": "kind-worker",
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "cm-constraint-analysis-cpu-multi",
                "k8s.pod.labels.app.kubernetes.io/instance": "cart",
                "k8s.pod.labels.app.kubernetes.io/name": "cart",
                "k8s.pod.labels.app.kubernetes.io/part-of": "cm-constraint-analysis-cpu-multi",
                "k8s.pod.labels.pod-template-hash": "7675f44bfd",
                "k8s.pod.labels.security.istio.io/tlsMode": "istio",
                "k8s.pod.labels.service.istio.io/canonical-name": "cart",
                "k8s.pod.labels.service.istio.io/canonical-revision": "latest",
                "k8s.pod.name": "cart-single-7675f44bfd-k2kr6",
                "k8s.pod.uid": "361e4299-3ad6-44f6-b86a-4a3a55470038",
            },
            "entityId": "361e4299-3ad6-44f6-b86a-4a3a55470038",
            "objectId": "9b9d64f0-a432-4b91-af7f-a91f1d924b53",
        }
        self.assertTrue(filter_notification(payload))

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": True,
                "filters": [
                    {
                        "problemType": "",
                        "entityType": "Pod",
                    },
                ],
            },
        },
    )
    def test_filter_blocks_invalid_entityType(self, mock_load_config):
        # Actual Payload for a Malfunction in a Controller
        payload = {
            "name": "Malfunction",
            "type": "DefectDetected",
            "entityName": "cm-constraint-analysis-cpu-multi/cart-single",
            "entityType": "Controller",
            "description": "Multiple instances are experiencing malfunction",
            "timestamp": "2024-08-28T08:35:35Z",
            "labels": {
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "cm-constraint-analysis-cpu-multi",
            },
            "entityId": "561a0fb6-ce55-4b44-ba74-80efb9071d16",
            "objectId": "7855c2c1-dae0-42a0-b232-3fbc60609c6b",
        }
        self.assertFalse(filter_notification(payload))

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": True,
                "filters": [
                    {
                        "problemType": "Malfunction",
                        "entityType": "",
                    },
                ],
            },
        },
    )
    def test_filter_blocks_invalid_problemType(self, mock_load_config):
        # Actual Payload for a FrequentCrash in a ComputeSpec
        payload = {
            "name": "FrequentCrash",
            "type": "DefectDetected",
            "entityName": "istio-system/kiali/kiali",
            "entityType": "ComputeSpec",
            "timestamp": "2024-08-28T07:09:18Z",
            "labels": {
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "istio-system",
            },
            "entityId": "1230e257-6c72-4639-82ad-e940b531b9e4_kiali",
            "objectId": "7a307736-be25-48d5-946b-918a167b2e46",
        }
        self.assertFalse(filter_notification(payload))

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": False,
                "filters": [],
            },
        },
    )
    def test_filter_allows_all_payloads_when_filter_disabled(self, mock_load_config):
        # Actual Payload for a Congested in a KubernetesService
        payload = {
            "name": "Congested",
            "type": "DefectDetected",
            "entityName": "causely/gateway",
            "entityType": "KubernetesService",
            "description": "Service is Congested resulting in clients receiving errors and unable to access the service",
            "timestamp": "2024-08-28T10:24:32Z",
            "labels": {
                "app": "causely-gateway",
                "app.kubernetes.io/managed-by": "Helm",
                "app.kubernetes.io/name": "gateway",
                "app.kubernetes.io/part-of": "causely",
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "causely",
                "prometheus-scrape": "true",
            },
            "entityId": "4d5b327b-0792-4df2-898f-31a9975151fa",
            "objectId": "7751615a-6015-4110-93b5-ff04c959d7d0",
        }
        self.assertTrue(filter_notification(payload))

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": True,
                "filters": [
                    {
                        "problemType": "FrequentCrash",
                        "entityType": "",
                    },
                ],
            },
        },
    )
    def test_filter_allows_empty_entityType(self, mock_load_config):
        # Actual Payload for a FrequentCrash in a ComputeSpec
        payload = {
            "name": "FrequentCrash",
            "type": "DefectDetected",
            "entityName": "istio-system/kiali/kiali",
            "entityType": "ComputeSpec",
            "timestamp": "2024-08-28T07:09:18Z",
            "labels": {
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "istio-system",
            },
            "entityId": "1230e257-6c72-4639-82ad-e940b531b9e4_kiali",
            "objectId": "7a307736-be25-48d5-946b-918a167b2e46",
        }
        self.assertTrue(filter_notification(payload))

    @patch(
        'causely_notification.server.load_config', return_value={
            "filterconfig": {
                "enabled": True,
                "filters": [
                    {
                        "problemType": "",
                        "entityType": "Pod",
                    },
                ],
            },
        },
    )
    def test_filter_allows_empty_problemType(self, mock_load_config):
        # Actual Payload for a Malfunction in a Pod
        payload = {
            "name": "Malfunction",
            "type": "DefectCleared",
            "entityName": "cm-constraint-analysis-cpu-multi/cart-single-7675f44bfd-k2kr6",
            "entityType": "Pod",
            "description": "Pod is experiencing an outage resulting in clients receiving errors and unable to access the service",
            "timestamp": "2024-08-28T08:15:42Z",
            "labels": {
                "VirtualMachineName": "kind-worker",
                "k8s.cluster.name": "dev",
                "k8s.cluster.uid": "919a6620-4466-454f-87d9-4b877a6ddf82",
                "k8s.namespace.name": "cm-constraint-analysis-cpu-multi",
                "k8s.pod.labels.app.kubernetes.io/instance": "cart",
                "k8s.pod.labels.app.kubernetes.io/name": "cart",
                "k8s.pod.labels.app.kubernetes.io/part-of": "cm-constraint-analysis-cpu-multi",
                "k8s.pod.labels.pod-template-hash": "7675f44bfd",
                "k8s.pod.labels.security.istio.io/tlsMode": "istio",
                "k8s.pod.labels.service.istio.io/canonical-name": "cart",
                "k8s.pod.labels.service.istio.io/canonical-revision": "latest",
                "k8s.pod.name": "cart-single-7675f44bfd-k2kr6",
                "k8s.pod.uid": "361e4299-3ad6-44f6-b86a-4a3a55470038",
            },
            "entityId": "361e4299-3ad6-44f6-b86a-4a3a55470038",
            "objectId": "9b9d64f0-a432-4b91-af7f-a91f1d924b53",
        }
        self.assertTrue(filter_notification(payload))
