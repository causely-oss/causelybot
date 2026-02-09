# Contributing to CauselyBot

Thank you for your interest in contributing. This document covers how to get involved, set up a development environment, and add a new webhook integration.

## How to contribute

- **Bug reports and feature requests:** Open an issue on GitHub describing the problem or idea.
- **Code changes:** Open a pull request (PR) against the default branch. Keep changes focused and include a short description. PRs must pass CI (tests and any lint/format checks).
- **Documentation:** Fixes or improvements to the README, this file, or in-code comments are welcome via the same PR process.

## Code of conduct

Be respectful and constructive. We aim to keep the project inclusive and professional.

## Development environment setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Git

### 1. Clone and create a virtual environment

```shell
git clone https://github.com/causely-oss/causelybot.git
cd causelybot
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```shell
pip install -r requirements.txt
```

For local development you may also want:

```shell
pip install pytest-cov   # run tests with coverage
```

### 3. Run tests

From the project root (with the venv activated):

```shell
pytest
```

Or with verbose output and coverage:

```shell
pytest -v --cov=causely_notification --cov-report=term-missing
```

Tests use `pytest.ini` (e.g. `testpaths = tests`, `pythonpath = .`), so no extra environment variables are required for discovery or imports.

### 4. Run the server locally (optional)

The server reads configuration from `/etc/causelybot/config.yaml` and webhook URLs/tokens from environment variables.

- Create a minimal config file, e.g.:

  ```shell
  sudo mkdir -p /etc/causelybot
  sudo tee /etc/causelybot/config.yaml << 'EOF'
  auth:
    token: "dev-token"
  webhooks:
    - name: "my-slack"
      hook_type: "slack"
      url: "https://example.com"
      token: ""
      filters:
        enabled: false
  EOF
  ```

- Set the URL (and token if needed) for the webhook. The server looks up `URL_<NORMALIZED_NAME>` where the name is uppercased and spaces become underscores (e.g. `my-slack` → `URL_MY-SLACK`):

  ```shell
  export AUTH_TOKEN=dev-token
  export URL_MY-SLACK=https://hooks.slack.com/services/...
  ```

- Run the app:

  ```shell
  python -m causely_notification.server
  ```

  The server listens on `http://0.0.0.0:5000`. Send a POST to `/webhook` with `Authorization: Bearer dev-token` and a JSON body matching the [notification payload](README.md#notification-payload) format.

### 5. Linting and formatting

The project uses pre-commit for style checks. Install hooks (optional):

```shell
pre-commit install
pre-commit run --all-files
```

You can also run individual tools (e.g. flake8, pytest) as in CI.

---

## Adding a new webhook integration

To add a new hook type (e.g. `pagerduty`), follow these steps so routing, config, and tests stay consistent.

### 1. Add the hook module

Create a new file under `causely_notification/` named after the integration, e.g. `pagerduty.py`.

- Implement a **single public function** that the server will call, with a consistent signature:

  - **With token (like Slack, Jira, OpsGenie):**  
    `forward_to_<name>(payload, url, token) -> requests.Response`
  - **Without token (like Teams):**  
    `forward_to_<name>(payload, url) -> requests.Response`

- The function should:
  - Build the outgoing request body (and headers if needed) from the Causely notification payload.
  - Use `causely_notification.utils.check_problem_detected(payload)` to distinguish ProblemDetected/ProblemUpdated vs ProblemCleared if the integration differentiates them.
  - Use `causely_notification.date.parse_iso_date` for any timestamp formatting.
  - Call `requests.post(url, json=..., headers=..., timeout=...)` and return the `response` object.

- The server treats HTTP **200, 201, and 202** as success; other status codes are treated as failures (and may trigger 207 or 500 from the server).

Use existing hooks as reference:

- **With token:** `slack.py`, `jira.py`, `opsgenie.py`
- **Without token:** `teams.py`

### 2. Register the hook in the server

In `causely_notification/server.py`:

1. **Import** the new forward function:

   ```python
   from causely_notification.pagerduty import forward_to_pagerduty
   ```

2. **Add a case** in the `match hook_type.lower():` block inside `webhook_routing()`:

   ```python
   case "pagerduty":
       response = forward_to_pagerduty(payload, hook_url, hook_token)
   ```

   (Omit `hook_token` if your integration does not use a token.)

### 3. Add standalone (adapter) tests

Create `tests/test_<name>.py` (e.g. `tests/test_pagerduty.py`) to test the adapter in isolation:

- **Mock `requests.post`** (patch `causely_notification.<name>.requests.post` so the mock is used when your code runs).
- Call `forward_to_<name>(payload, url, token)` (or without `token`) with one or more sample payloads.
- Assert:
  - The HTTP response status (e.g. 200 or 202).
  - That `requests.post` was called with the expected URL (and optionally headers).
  - That the JSON body sent to the external API contains the right fields (e.g. title, description, severity) derived from the Causely payload.

Include at least:

- One test for a **ProblemDetected** (or ProblemUpdated) payload.
- One test for a **ProblemCleared** payload if your formatter differs for that case.

Use `tests/test_jira.py`, `tests/test_opsgenie.py`, or `tests/test_teams.py` as templates.

### 4. Include the new backend in unified server tests

In `tests/test_server.py`:

1. **Add the backend to the list and status map:**

   ```python
   BACKENDS = ["slack", "teams", "jira", "opsgenie", "pagerduty"]
   BACKEND_SUCCESS_STATUS = {
       ...
       "pagerduty": 200,  # or 201 / 202 depending on the API
   }
   ```

2. **Set the test URL env var** at the top (same pattern as existing hooks):

   ```python
   os.environ["URL_PAGERDUTY-TEST"] = "http://test_pagerduty"
   ```

3. **Adjust `_expected_url()`** if the integration uses a path suffix (e.g. Jira uses `{base}/rest/api/2/issue`). If the hook uses the URL as-is, no change is needed.

4. **Token in config:** If the hook expects a token, add it in `_one_webhook_config()` for the new `hook_type` (e.g. in the same condition as `"slack", "jira", "opsgenie"`).

The existing parameterized tests in `test_server.py` (e.g. `test_webhook_posts_expected_payload`, `test_webhook_posts_expected_payload_filtered`) will then run for the new backend as well, so routing and filtering are covered without extra test code.

### 5. Update documentation

- In the main **README**, add the new hook type to the list of supported `hook_type` values (e.g. in the Configure Webhook section and in the Appendix).
- If there are setup or config quirks, add a short note or subsection.

### Checklist summary

- [ ] New module `causely_notification/<name>.py` with `forward_to_<name>(...)` returning `requests.Response`.
- [ ] `server.py`: import and new `case "<name>":` in the match block.
- [ ] `tests/test_<name>.py`: adapter tests with mocked `requests.post`, asserting URL, body, and status.
- [ ] `tests/test_server.py`: add to `BACKENDS`, `BACKEND_SUCCESS_STATUS`, env var, and `_expected_url` / token config if needed.
- [ ] README (and CONTRIBUTING if needed): document the new hook type.

Running `pytest` after these steps should show the new backend in the parameterized server tests and your new adapter tests passing.
