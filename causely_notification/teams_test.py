import unittest
import json
from unittest.mock import patch, MagicMock
from causely_notification.teams import forward_to_teams

# Dummy implementations to make testable
def create_teams_detected_payload(payload):
    payload = ''
    return {"text": f"Problem detected: {payload['message']}"}

def create_teams_cleared_payload(payload):
    return {"text": f"Problem cleared: {payload['message']}"}

class TestForwardToTeams(unittest.TestCase):

    @patch('requests.post')
    def test_forward_to_teams_detected(self, mock_post):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        payload = {
            "link": "https://portal.staging.causely.app/rootCauses/d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "name": "Malfunction",
            "type": "ProblemDetected",
            "entity": {
                "id": "ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "link": "https://portal.staging.causely.app/observe/topology/ac462ed5-87cb-5a1a-9586-b2951b52adda",
                "name": "/webhook/teams",
                "type": "HTTPPath"
            },
            "labels": {
                "causely.ai/service-id": "fdea69a6-7ae3-504c-a5f9-cd450d135672",
                "causely.ai/service-name": "causelybot"
            },
            "objectId": "d76f027d-e697-46ed-8a2c-f16356a97ceb",
            "severity": "Medium",
            "timestamp": "2025-08-07T18:51:54.164185287Z",
            "description": {
                "details": "A higher error rate can stem from multiple factors...",
                "summary": "The HTTP path is experiencing a high rate of errors...",
                "remediationOptions": [
                    {
                        "title": "Check Logs",
                        "description": "Inspect the application logs..."
                    }
                ]
            }
        }
        url = "https://fake.teams.url/webhook"

        response = forward_to_teams(payload, url)

        self.assertEqual(response.status_code, 200)
        clear_payload = {
          "link": "https://portal.staging.causely.app/rootCauses/71dd427c-c95e-45b1-a72e-db2d15a3eb58",
          "name": "Congested",
          "type": "ProblemCleared",
          "entity": {
            "id": "90719b30-95b3-5eac-8601-58813910ddb6",
            "link": "https://portal.staging.causely.app/observe/topology/90719b30-95b3-5eac-8601-58813910ddb6",
            "name": "causely-staging/victoriametrics",
            "type": "Service"
          },
          "labels": {
            "k8s.cluster.uid": "b0b2162a-ce5b-44ea-9dac-b4380b99f614",
            "k8s.cluster.name": "chaos1",
            "causely.ai/cluster": "chaos1",
            "causely.ai/project": "causely-staging",
            "causely.ai/service": "victoriametrics",
            "k8s.namespace.name": "causely-staging",
            "causely.ai/namespace": "causely-staging",
            "process.runtime.name": "go",
            "causely.ai/service-type": "StatefulSet",
            "causely.ai/owner-scraper": "KubernetesController",
            "causely.ai/cloud-provider": "aws"
          },
          "objectId": "71dd427c-c95e-45b1-a72e-db2d15a3eb58",
          "severity": "Medium",
          "timestamp": "2025-08-07T19:07:29.416709Z",
          "description": {
            "details": "Congestion often occurs when the service receives more requests than it can handle within its capacity, leading to bottlenecks in processing. This may be due to insufficient resources (e.g., CPU, memory, or bandwidth), unoptimized code, or a surge in traffic (e.g., due to a sudden increase in demand or DDoS attack).\n",
            "summary": "The service is experiencing congestion, resulting in high latency for clients. This suggests that the system is unable to handle the current load efficiently, causing delays in response times.",
            "remediationOptions": [
              {
                "title": "Scale Resources Appropriately",
                "description": "Increase the application's processing capacity by scaling vertically (upgrading hardware) or horizontally (adding more instances) to handle higher data volumes and reduce lag.\n"
              }
            ]
          },
          "duration_ns": 369506251438
        }
        response = forward_to_teams(clear_payload, url)

        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
