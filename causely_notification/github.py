"""
GitHub integration: create or find GitHub issues for Causely root cause events.

Follows the same behavior as the server.js blueprint:
- Only creates issues for ProblemUpdated or ProblemDetected.
- Deduplicates by root cause objectId (Causely Root Cause ID in issue body).
- Supports assigning to Copilot (copilot-swe-agent) via GraphQL when REST returns 422.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import requests

RC_ID_MARKER = "Causely Root Cause ID: "
COPILOT_LOGIN = "copilot-swe-agent"
GITHUB_API_BASE = "https://api.github.com"


def _github_headers(token, extra=None):
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def github_request(path, token, method="GET", json_body=None):
    url = f"{GITHUB_API_BASE}{path}"
    resp = requests.request(
        method,
        url,
        headers=_github_headers(token),
        json=json_body,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"GitHub API {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else None


def github_graphql(token, query, variables=None):
    resp = requests.post(
        f"{GITHUB_API_BASE}/graphql",
        headers={
            **_github_headers(token),
            "GraphQL-Features": "issues_copilot_assignment_api_support",
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    data = resp.json()
    if isinstance(data, dict) and data.get("errors"):
        raise RuntimeError(
            "GraphQL: " + "; ".join(e.get("message", str(e)) for e in data["errors"])
        )
    if not resp.ok:
        raise RuntimeError(f"GraphQL HTTP {resp.status_code}: {data}")
    return data.get("data")


def get_repo_and_copilot_ids(owner, repo, token):
    """Get repository node ID and Copilot bot ID for GraphQL issue creation with assignee."""
    data = github_graphql(
        token,
        """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
            suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
              nodes {
                login
                __typename
                ... on Bot { id }
              }
            }
          }
        }
        """,
        {"owner": owner, "name": repo},
    )
    repo_data = (data or {}).get("repository")
    if not repo_data:
        return None
    nodes = (repo_data.get("suggestedActors") or {}).get("nodes") or []
    copilot = next((n for n in nodes if n and n.get("login") == COPILOT_LOGIN), None)
    return {
        "repo_id": repo_data["id"],
        "copilot_id": copilot.get("id") if copilot else None,
    }


def find_existing_issue_for_root_cause(object_id, owner, repo, token):
    """Return {number, url} of an open issue whose body contains RC_ID_MARKER + object_id, else None."""
    page = 1
    per_page = 100
    while True:
        issues = github_request(
            f"/repos/{owner}/{repo}/issues?state=open&per_page={per_page}&page={page}",
            token,
        )
        for issue in issues:
            if issue.get("pull_request"):
                continue
            body = issue.get("body") or ""
            if RC_ID_MARKER + object_id in body:
                return {"number": issue["number"], "url": issue.get("html_url", "")}
        if len(issues) < per_page:
            break
        page += 1
    return None


def _build_issue_body(payload):
    object_id = payload.get("objectId", "")
    name = payload.get("name") or "Root cause"
    entity = payload.get("entity") or {}
    entity_name = entity.get("name") or entity.get("id") or "unknown"
    link = payload.get("link") or ""
    desc = payload.get("description") or {}
    summary = desc.get("summary") or ""
    details = desc.get("details") or ""
    remediation_options = desc.get("remediationOptions") or []
    severity = payload.get("severity") or ""
    timestamp = payload.get("timestamp") or ""

    parts = [
        "## Causely Root Cause",
        RC_ID_MARKER + object_id,
        "",
        f"**Portal:** {link}",
        f"**Entity:** {entity_name}",
        f"**Severity:** {severity}",
        f"**Detected:** {timestamp}",
        "",
        "### Summary",
        summary,
        "",
        "### Details",
        details,
    ]
    if remediation_options:
        rem_text = "\n### Remediation options\n" + "\n".join(
            f"- **{r.get('title', '')}**\n  {(r.get('description') or '').replace(chr(10), chr(10) + '  ')}"
            for r in remediation_options
        )
        parts.append(rem_text)
    return "\n".join(p for p in parts if p is not None)


def create_issue_for_root_cause(payload, owner, repo, token, assignee=None):
    """Create a GitHub issue for the root cause. Returns dict with number and url."""
    object_id = payload.get("objectId", "")
    name = payload.get("name") or "Root cause"
    entity = payload.get("entity") or {}
    entity_name = entity.get("name") or entity.get("id") or "unknown"
    title = f"[Causely] {name}: {entity_name}"[:256]
    body = _build_issue_body(payload)

    assign_to_copilot = assignee and assignee.strip() == COPILOT_LOGIN

    if assign_to_copilot:
        ids = get_repo_and_copilot_ids(owner, repo, token)
        if ids and ids.get("copilot_id"):
            data = github_graphql(
                token,
                """
                mutation($repoId: ID!, $title: String!, $body: String!, $assigneeIds: [ID!]) {
                  createIssue(input: {
                    repositoryId: $repoId,
                    title: $title,
                    body: $body,
                    assigneeIds: $assigneeIds
                  }) {
                    issue { number url }
                  }
                }
                """,
                {
                    "repoId": ids["repo_id"],
                    "title": title,
                    "body": body,
                    "assigneeIds": [ids["copilot_id"]],
                },
            )
            issue = (data or {}).get("createIssue", {}).get("issue")
            if issue:
                return {"number": issue["number"], "url": issue["url"]}
        print(
            f"[webhook] {COPILOT_LOGIN} not in suggestedActors for repo; creating issue without assignee",
            file=sys.stderr,
        )

    # REST: create issue (no assignee or non-Copilot assignee)
    created = github_request(
        f"/repos/{owner}/{repo}/issues",
        token,
        method="POST",
        json_body={
            "title": title,
            "body": body,
            **(
                {"assignees": [assignee]} if assignee and not assign_to_copilot else {}
            ),
        },
    )
    url = created.get("html_url", "")
    number = created.get("number", 0)

    if assignee and not assign_to_copilot:
        try:
            github_request(
                f"/repos/{owner}/{repo}/issues/{number}",
                token,
                method="PATCH",
                json_body={"assignees": [assignee]},
            )
        except Exception as e:
            if "422" in str(e):
                print(
                    f"[webhook] could not assign to {assignee}; issue created without assignee",
                    file=sys.stderr,
                )
            else:
                raise

    return {"number": number, "url": url}


def forward_to_github(payload, repo_spec, token, assignee=None):
    """
    Ensure a GitHub issue exists for this root cause (ProblemUpdated or ProblemDetected).
    repo_spec should be "owner/repo". Returns a response-like object with .status_code.
    """
    print(payload, file=sys.stderr)
    print(payload.get("type"), file=sys.stderr)

    event_type = payload.get("type")
    if event_type not in ("ProblemUpdated", "ProblemDetected"):
        return SimpleNamespace(status_code=200, content=b"", text="ignored event type")

    object_id = payload.get("objectId")
    if not object_id:
        return SimpleNamespace(
            status_code=400, content=b"missing objectId", text="missing objectId"
        )

    parts = repo_spec.strip().split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return SimpleNamespace(
            status_code=500,
            content=b"invalid repo_spec",
            text="GITHUB repo_spec must be owner/repo",
        )

    owner, repo = parts[0], parts[1]

    try:
        existing = find_existing_issue_for_root_cause(object_id, owner, repo, token)
        if existing:
            print(
                f"[webhook] issue already exists for root cause {object_id}: {existing['url']} (#{existing['number']}), skipping",
                file=sys.stderr,
            )
            return SimpleNamespace(status_code=200, content=b"", text="existing")
        issue = create_issue_for_root_cause(
            payload, owner, repo, token, assignee=(assignee or "").strip() or None
        )
        print(
            f"[webhook] created issue for root cause {object_id}: {issue['url']} (#{issue['number']})",
            file=sys.stderr,
        )
        return SimpleNamespace(status_code=201, content=b"", text=issue["url"])
    except Exception as e:
        print(f"[webhook] GitHub error: {e}", file=sys.stderr)
        return SimpleNamespace(
            status_code=500, content=str(e).encode(), text=str(e)
        )
