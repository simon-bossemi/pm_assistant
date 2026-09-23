"""Generate the dashboard's reproducible management narrative from refresh facts."""

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[1]
SITE = ROOT / "sites" / "master-plan" / "dist"
FACTS = ROOT / "work_notes" / "master-plan-refresh-facts.json"


def section(rows: dict[str, dict], name: str, summary: str) -> dict:
    value = rows.get(name, {})
    statuses = value.get("statuses", {})
    return {
        "name": name,
        "tickets": value.get("tickets", 0),
        "toDo": statuses.get("To Do", 0),
        "inProgress": statuses.get("In Progress", 0),
        "preSiliconDone": statuses.get("Pre-silicon Done", 0),
        "resolved": statuses.get("Resolved", 0),
        "reopened": statuses.get("Reopened", 0),
        "done": statuses.get("Done", 0),
        "overdue": value.get("overdue", 0),
        "missingDue": value.get("missingDueDate", 0),
        "missingAssignee": value.get("missingAssignee", 0),
        "summary": summary,
    }


def main() -> None:
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    doc = json.loads((SITE / "doc-controls.json").read_text(encoding="utf-8"))
    rows = {value["name"]: value for value in facts["sections"]}
    statuses = facts["statuses"]
    focus = ["SDK", "Host SW", "AI Model Dev. Tools for Eagle N", "Ref. Models"]
    focus_total = sum(rows.get(name, {}).get("tickets", 0) for name in focus)
    report = {
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "sourceObservedAt": facts["observedAt"],
        "title": "Eagle B0 ticket and documentation control",
        "overall": (
            f"Jira filter 19455 contains {facts['tickets']} tickets: "
            f"{statuses.get('To Do', 0)} To Do, {statuses.get('In Progress', 0)} In Progress, "
            f"{statuses.get('Pre-silicon Done', 0)} Pre-silicon Done and {statuses.get('Done', 0)} Done. "
            f"The four requested Level 1 areas account for {focus_total} tickets: "
            f"SDK {rows.get('SDK', {}).get('tickets', 0)}, Host SW {rows.get('Host SW', {}).get('tickets', 0)}, "
            f"AI Model Dev. Tools for Eagle N {rows.get('AI Model Dev. Tools for Eagle N', {}).get('tickets', 0)} "
            f"and Ref. Models {rows.get('Ref. Models', {}).get('tickets', 0)}. "
            f"{facts['overdue']} overdue tickets, {facts['missingDueDate']} missing due dates and "
            f"{facts['missingAssignee']} missing assignee require management review. "
            "No filter ticket is currently recorded as Resolved or Reopened. "
            "The documentation sheet contributes 24 SRS/SAD/SUD writing and review pairs; "
            "direct Jira reads cover document keys outside filter 19455."
        ),
        "attention": [
            f"Review the {facts['overdue']} overdue Jira tickets and agree an owner and recovery date.",
            f"Assign the {facts['missingAssignee']} Host SW ticket without a Jira assignee before using its date as a commitment.",
            f"Resolve or confirm the {facts['missingDueDate']} missing Jira due dates, starting with the overdue SDK tickets and the missing Ref. Models date.",
            "Confirm the 24 documentation writing/review pairs and keep review status and reviewer assignment visible after each writing ticket reaches Jira P-D.",
            "Use the seven ITCP-47 child test requests as the test-request evidence set for P-D feature follow-up; wording-based matches remain review aids until a human confirms the relationship.",
        ],
        "sections": [
            section(rows, "SDK", "The SDK cohort contains 17 filter tickets: three are Pre-silicon Done, three are Done, and eleven remain To Do. Two tickets are overdue and four have no usable Jira due date."),
            section(rows, "Host SW", "Host SW contains 33 filter tickets. Fourteen are Pre-silicon Done, three are In Progress and sixteen remain To Do; one ticket has no assignee."),
            section(rows, "AI Model Dev. Tools for Eagle N", "The AI model development tools cohort contains nine tickets split evenly across To Do, In Progress and Pre-silicon Done."),
            section(rows, "Ref. Models", "Ref. Models contains 17 tickets: nine are Pre-silicon Done, five are In Progress and three remain To Do. One Jira due date is missing."),
            section(rows, "Other filter tickets", "These 50 tickets are retained for filter-wide control views but are not mapped to one of the four requested Level 1 areas in the current workbook. They include three overdue tickets and seventeen missing due dates."),
        ],
        "documentation": {
            "pairs": len(doc.get("pairs", [])),
            "reviewActions": sum(1 for pair in doc.get("pairs", []) if pair.get("reviewControl", {}).get("action")),
            "writingReviewRule": "When a writing ticket is Jira P-D, its paired review ticket must be In Progress and assigned.",
            "testEpic": "ITCP-47",
            "testRequests": len(doc.get("tests", {}).get("children", [])),
        },
        "limitations": "Jira status and due dates are the current ticket evidence. Workbook P-D and Done dates are targets and support mapping; they do not prove completion. Documentation controls read document ticket keys directly because not all of them carry the filter label. No Jira status, assignee or link is changed by this dashboard. Refresh remains on request through Codex.",
    }
    (SITE / "ai-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tickets": facts["tickets"], "focusTickets": focus_total, "output": str(SITE / "ai-report.json")}))


if __name__ == "__main__":
    main()
