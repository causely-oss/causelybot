#!/bin/bash
# Copyright 2025 Causely, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

set -e

CONTAINER_NAME="causelybot-test"
IMAGE_NAME="${1:-us-docker.pkg.dev/public-causely/public/bot:latest}"
PORT="${2:-5001}"
AUTH_TOKEN="test-token-123"

echo "Testing Docker image: $IMAGE_NAME"

# Start container
echo "Starting container..."
docker run --rm -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:5000" \
  -v "$(pwd)/config.sample.yaml:/etc/causelybot/config.yaml:ro" \
  -e AUTH_TOKEN="$AUTH_TOKEN" \
  -e URL_DEBUG=http://localhost:5000/webhook \
  -e TOKEN_DEBUG=dummy-token \
  "$IMAGE_NAME"

# Cleanup on exit
cleanup() {
  echo "Cleaning up..."
  docker stop "$CONTAINER_NAME" 2>/dev/null || true
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for container to be healthy
echo "Waiting for container to be ready..."
for i in {1..30}; do
  if curl -f http://localhost:$PORT/webhook \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"type":"test"}' 2>/dev/null; then
    echo "✓ Container is healthy"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "✗ Container failed to become healthy after 30 seconds"
    echo "Container logs:"
    docker logs "$CONTAINER_NAME"
    exit 1
  fi
  echo "  Attempt $i/30..."
  sleep 1
done

# Test webhook endpoint
echo "Testing webhook endpoint..."
response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:$PORT/webhook \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ProblemDetected",
    "problem_id": "test-123",
    "severity": "high",
    "title": "Test Alert"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response code: $http_code"
echo "Response body: $body"

# Expect 200 (success) or 207 (partial success)
if [[ "$http_code" == "200" ]] || [[ "$http_code" == "207" ]]; then
  echo "✓ Webhook test passed"
  exit 0
else
  echo "✗ Webhook test failed with code $http_code"
  exit 1
fi
