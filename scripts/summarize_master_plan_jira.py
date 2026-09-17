"""Calculate reproducible dashboard facts from the latest Jira capture."""

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).parents[1]
HISTORY = ROOT / "sites" / "master-plan" / "dist" / "jira-history.json"
OUTPUT = ROOT / "work_notes" / "master-plan-refresh-facts.json"


def status_name(value):
    value = str(value or "").strip().lower()
    if "progress" in value:
        return "In Progress"
    if "pre-silicon" in value or value == "p-d":
        return "Pre-silicon Done"
    if value == "resolved":
        return "Resolved"
    if "reopen" in value:
        return "Reopened"
    if value in {"done", "closed"}:
        return "Done"
    return "To Do"


def main():
    capture = json.loads(HISTORY.read_text(encoding="utf-8"))
    issues = capture.get("issues", [])
    today = date.today().isoformat()
    statuses = Counter(status_name(issue.get("currentStatus")) for issue in issues)
    sections = defaultdict(list)
    for issue in issues:
        sections[issue.get("section") or "Unmapped Jira ticket"].append(issue)

    section_facts = []
    for name, rows in sorted(sections.items(), key=lambda item: (-len(item[1]), item[0])):
        counts = Counter(status_name(row.get("currentStatus")) for row in rows)
        section_facts.append({
            "name": name,
            "tickets": len(rows),
            "statuses": dict(counts),
            "overdue": sum(bool(row.get("dueDate")) and row["dueDate"] < today and status_name(row.get("currentStatus")) != "Done" for row in rows),
            "missingDueDate": sum(not row.get("dueDate") for row in rows),
            "missingAssignee": sum(not row.get("assignee") for row in rows),
        })

    facts = {
        "filterId": capture.get("filterId"),
        "jql": capture.get("jql"),
        "observedAt": capture.get("observedAt"),
        "calculatedAsOf": today,
        "tickets": len(issues),
        "statuses": dict(statuses),
        "overdue": sum(section["overdue"] for section in section_facts),
        "missingDueDate": sum(section["missingDueDate"] for section in section_facts),
        "missingAssignee": sum(section["missingAssignee"] for section in section_facts),
        "sections": section_facts,
        "historyEvents": len(capture.get("changes", [])),
        "reportArtifact": str(ROOT / "sites" / "master-plan" / "dist" / "ai-report.json"),
        "reportInstruction": "Codex must regenerate ai-report.json from these facts before building and publishing.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "tickets": len(issues), "sections": len(section_facts), "overdue": facts["overdue"]}))


if __name__ == "__main__":
    main()
