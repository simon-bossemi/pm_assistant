from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required setting: {name}")
    return value


def session() -> requests.Session:
    load_dotenv(ENV_PATH)
    base_url = require_env("JIRA_BASE_URL").rstrip("/")
    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")
    s = requests.Session()
    s.trust_env = os.getenv("JIRA_TRUST_ENV_PROXY", "false").strip().lower() in {"1", "true", "yes"}
    s.auth = (email, token)
    s.headers.update({"Accept": "application/json"})
    s.base_url = base_url  # type: ignore[attr-defined]
    return s


def output_root() -> Path:
    load_dotenv(ENV_PATH)
    return Path(os.getenv("JIRA_OUTPUT_ROOT", str(ROOT.parent.parent / "jira")))


def list_projects() -> dict[str, Any]:
    s = session()
    projects: list[dict[str, Any]] = []
    start_at = 0
    max_results = 50
    while True:
        response = s.get(
            f"{s.base_url}/rest/api/3/project/search",
            params={"startAt": start_at, "maxResults": max_results},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        values = payload.get("values", [])
        projects.extend(values)
        if start_at + len(values) >= payload.get("total", len(projects)) or not values:
            break
        start_at += len(values)
    return {"projects": projects}


def search_issues(jql: str, max_results: int) -> dict[str, Any]:
    s = session()
    response = s.post(
        f"{s.base_url}/rest/api/3/search/jql",
        json={
            "jql": jql,
            "maxResults": max_results,
            "fields": [
                "summary",
                "status",
                "assignee",
                "issuetype",
                "project",
                "priority",
                "updated",
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_issue(issue_key: str) -> dict[str, Any]:
    s = session()
    response = s.get(
        f"{s.base_url}/rest/api/3/issue/{issue_key}",
        params={
            "fields": ",".join(
                [
                    "summary",
                    "description",
                    "status",
                    "assignee",
                    "reporter",
                    "issuetype",
                    "project",
                    "priority",
                    "updated",
                    "created",
                    "comment",
                    "labels",
                ]
            )
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def adf_paragraph(text: str) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": line}] if line else [],
    }


def text_to_adf(text: str) -> dict[str, Any]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return {
        "type": "doc",
        "version": 1,
        "content": [adf_paragraph(line) for line in lines] or [adf_paragraph("")],
    }


def create_issue(project_key: str, issue_type: str, summary: str, description: str) -> dict[str, Any]:
    s = session()
    response = s.post(
        f"{s.base_url}/rest/api/3/issue",
        json={
            "fields": {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": summary,
                "description": text_to_adf(description),
            }
        },
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def write_json(name: str, payload: dict[str, Any]) -> Path:
    root = output_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def render_projects_md(payload: dict[str, Any]) -> str:
    projects = payload.get("projects", [])
    lines = ["# Jira Projects", "", f"- Count: {len(projects)}", "", "## Projects"]
    for project in projects:
        lines.append(
            f"- {project.get('key', '')}: {project.get('name', '')}"
        )
    lines.append("")
    return "\n".join(lines)


def render_issues_md(payload: dict[str, Any], jql: str) -> str:
    issues = payload.get("issues", [])
    lines = ["# Jira Issue Search", "", f"- JQL: {jql}", f"- Count: {len(issues)}", "", "## Issues"]
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")
        status = (fields.get("status") or {}).get("name", "")
        project = (fields.get("project") or {}).get("key", "")
        lines.append(
            f"- {issue.get('key', '')} [{project}] {fields.get('summary', '')} | {status} | {assignee}"
        )
    lines.append("")
    return "\n".join(lines)


def adf_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(part for part in (adf_to_text(item) for item in node) if part)
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")
    if node_type in {"paragraph", "heading", "blockquote", "listItem"}:
        return "".join(adf_to_text(item) for item in node.get("content", []))
    if node_type in {"bulletList", "orderedList"}:
        return "\n".join(adf_to_text(item) for item in node.get("content", []))
    if node_type == "hardBreak":
        return "\n"
    if node_type == "doc":
        return "\n".join(part for part in (adf_to_text(item) for item in node.get("content", [])) if part)
    return "".join(adf_to_text(item) for item in node.get("content", []))


def render_issue_detail_md(payload: dict[str, Any]) -> str:
    fields = payload.get("fields", {})
    description = adf_to_text(fields.get("description")) or "(no description)"
    comments = ((fields.get("comment") or {}).get("comments")) or []

    lines = [
        f"# {payload.get('key', '')}: {fields.get('summary', '')}",
        "",
        f"- Project: {(fields.get('project') or {}).get('key', '')}",
        f"- Type: {(fields.get('issuetype') or {}).get('name', '')}",
        f"- Status: {(fields.get('status') or {}).get('name', '')}",
        f"- Priority: {(fields.get('priority') or {}).get('name', '')}",
        f"- Assignee: {((fields.get('assignee') or {}).get('displayName')) or 'Unassigned'}",
        f"- Reporter: {((fields.get('reporter') or {}).get('displayName')) or 'Unknown'}",
        f"- Created: {fields.get('created', '')}",
        f"- Updated: {fields.get('updated', '')}",
        "",
        "## Description",
        description,
        "",
        "## Comments",
    ]

    if not comments:
        lines.append("- No comments.")
    else:
        for comment in comments:
            author = ((comment.get("author") or {}).get("displayName")) or "Unknown"
            created = comment.get("created", "")
            body = adf_to_text(comment.get("body")) or "(empty comment)"
            lines.extend(
                [
                    f"- {author} ({created})",
                    body,
                    "",
                ]
            )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Jira projects and issues.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("projects", help="List accessible Jira projects.")

    search = sub.add_parser("search", help="Search Jira issues with JQL.")
    search.add_argument("--jql", required=True)
    search.add_argument("--max-results", type=int, default=25)

    issue = sub.add_parser("issue", help="Read a Jira issue in detail.")
    issue.add_argument("--key", required=True)

    create = sub.add_parser("create", help="Create a Jira issue.")
    create.add_argument("--project-key", required=True)
    create.add_argument("--issue-type", required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--description", required=True)

    args = parser.parse_args()

    try:
        if args.command == "projects":
            payload = list_projects()
            json_path = write_json("jira-projects.json", payload)
            md_path = output_root() / "jira-projects.md"
            md_path.write_text(render_projects_md(payload), encoding="utf-8")
            print(json.dumps({"json_path": str(json_path), "markdown_path": str(md_path), "count": len(payload.get("projects", []))}, indent=2))
            return 0

        if args.command == "issue":
            payload = get_issue(args.key)
            json_path = write_json(f"{args.key}-issue.json", payload)
            md_path = output_root() / f"{args.key}-issue.md"
            md_path.write_text(render_issue_detail_md(payload), encoding="utf-8")
            print(json.dumps({"json_path": str(json_path), "markdown_path": str(md_path), "key": payload.get("key")}, indent=2))
            return 0

        if args.command == "create":
            payload = create_issue(args.project_key, args.issue_type, args.summary, args.description)
            json_path = write_json("jira-create-issue.json", payload)
            print(json.dumps({"json_path": str(json_path), "id": payload.get("id"), "key": payload.get("key"), "self": payload.get("self")}, indent=2))
            return 0

        payload = search_issues(args.jql, args.max_results)
        json_path = write_json("jira-search.json", payload)
        md_path = output_root() / "jira-search.md"
        md_path.write_text(render_issues_md(payload, args.jql), encoding="utf-8")
        print(json.dumps({"json_path": str(json_path), "markdown_path": str(md_path), "count": len(payload.get("issues", []))}, indent=2))
        return 0
    except requests.HTTPError as exc:
        body = exc.response.text[:500] if exc.response is not None else str(exc)
        print(f"Jira request failed: {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
