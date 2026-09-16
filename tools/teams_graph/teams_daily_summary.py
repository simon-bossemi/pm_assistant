import argparse
import html
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from zoneinfo import ZoneInfo

import teams_graph_reader as graph_reader


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEZONE = os.getenv("PM_TIMEZONE", "Asia/Seoul")
DEFAULT_OUTPUT_DIR = Path(os.getenv("PM_TEAMS_SUMMARY_DIR", "outputs"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a daily markdown summary of Teams chats for a target date."
    )
    parser.add_argument("--auth-mode", choices=["device_code", "client_credentials"], default=os.getenv("MS_AUTH_MODE", "device_code"))
    parser.add_argument("--tenant-id", default=os.getenv("MS_TENANT_ID"))
    parser.add_argument("--client-id", default=os.getenv("MS_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("MS_CLIENT_SECRET"))
    parser.add_argument("--user-id", default=os.getenv("MS_USER_ID"))
    parser.add_argument("--date", default=date.today().isoformat(), help="Target local date in YYYY-MM-DD format.")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="IANA timezone name used for daily filtering.")
    parser.add_argument("--max-chats", type=int, default=20, help="Maximum number of chats to inspect.")
    parser.add_argument("--page-size", type=int, default=50, help="Maximum messages per Graph page.")
    parser.add_argument("--max-pages-per-chat", type=int, default=4, help="Maximum pages to fetch per chat.")
    parser.add_argument("--chat-id", action="append", help="Optional specific chat ID. Repeat to summarize only selected chats.")
    parser.add_argument("--output-file", help="Optional explicit output markdown path.")
    return parser


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_graph_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def local_day_bounds(target_day: str, tz_name: str) -> tuple[datetime, datetime, date, ZoneInfo]:
    tz = ZoneInfo(tz_name)
    parsed_day = date.fromisoformat(target_day)
    start_local = datetime.combine(parsed_day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC")), parsed_day, tz


def graph_get_url(access_token: str, url: str) -> Dict[str, Any]:
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=60)
    response.raise_for_status()
    return response.json()


def list_chats(args: argparse.Namespace, access_token: str) -> List[Dict[str, Any]]:
    if args.chat_id:
        chats: List[Dict[str, Any]] = []
        for chat_id in args.chat_id:
            chats.append({"id": chat_id, "chatType": "unknown", "topic": ""})
        return chats

    request = argparse.Namespace(
        auth_mode=args.auth_mode,
        top=args.max_chats,
        user_id=args.user_id,
    )
    payload = graph_reader.list_chats(request, access_token)
    return payload.get("value", [])


def build_messages_url(args: argparse.Namespace, chat_id: str, page_size: int, start_utc: datetime, end_utc: datetime) -> str:
    order_expr = "createdDateTime desc"
    filter_expr = (
        f"createdDateTime lt {end_utc.isoformat().replace('+00:00', 'Z')} "
        f"and createdDateTime gt {start_utc.isoformat().replace('+00:00', 'Z')}"
    )
    query = {
        "$top": page_size,
        "$orderby": order_expr,
        "$filter": filter_expr,
    }

    path = f"/me/chats/{chat_id}/messages" if args.auth_mode == "device_code" else f"/chats/{chat_id}/messages"
    return f"{GRAPH_BASE_URL}{path}?{graph_reader.urlencode(query)}"


def fetch_messages_for_day(
    args: argparse.Namespace,
    access_token: str,
    chat_id: str,
    start_utc: datetime,
    end_utc: datetime,
) -> List[Dict[str, Any]]:
    url = build_messages_url(args, chat_id, args.page_size, start_utc, end_utc)
    collected: List[Dict[str, Any]] = []
    pages = 0

    while url and pages < args.max_pages_per_chat:
        payload = graph_get_url(access_token, url)
        collected.extend(payload.get("value", []))
        url = payload.get("@odata.nextLink")
        pages += 1

    return collected


def topic_for_chat(chat: Dict[str, Any]) -> str:
    return chat.get("topic") or chat.get("id", "")


def summarize_without_llm(chat_messages: Dict[str, List[Dict[str, Any]]], tz: ZoneInfo) -> str:
    lines: List[str] = []
    total_messages = sum(len(messages) for messages in chat_messages.values())
    total_chats = len(chat_messages)
    speaker_counts: Counter[str] = Counter()

    for messages in chat_messages.values():
        for message in messages:
            speaker_counts[message["sender"]] += 1

    lines.append(f"- Total chats with activity: {total_chats}")
    lines.append(f"- Total messages captured: {total_messages}")
    if speaker_counts:
        top_speakers = ", ".join(f"{name} ({count})" for name, count in speaker_counts.most_common(5))
        lines.append(f"- Most active senders: {top_speakers}")

    for chat_name, messages in sorted(chat_messages.items()):
        lines.append("")
        lines.append(f"## {chat_name}")
        lines.append(f"- Messages: {len(messages)}")
        local_times = [parse_graph_datetime(m["createdDateTime"]).astimezone(tz).strftime("%H:%M") for m in messages]
        if local_times:
            lines.append(f"- Activity window: {local_times[-1]} to {local_times[0]}")

        per_sender = Counter(m["sender"] for m in messages)
        if per_sender:
            lines.append(
                f"- Active participants: {', '.join(f'{name} ({count})' for name, count in per_sender.most_common(4))}"
            )

        actions: List[str] = []
        for message in messages[:5]:
            content = message["text"]
            if content:
                actions.append(f"- {message['sender']}: {content[:180]}")
        lines.extend(actions)

    return "\n".join(lines).strip()


def build_llm_prompt(target_day: str, chat_messages: Dict[str, List[Dict[str, Any]]], tz_name: str) -> str:
    payload = []
    for chat_name, messages in chat_messages.items():
        payload.append(
            {
                "chat": chat_name,
                "messages": [
                    {
                        "time": parse_graph_datetime(m["createdDateTime"]).astimezone(ZoneInfo(tz_name)).strftime("%H:%M"),
                        "sender": m["sender"],
                        "text": m["text"],
                    }
                    for m in messages
                ],
            }
        )

    return (
        f"Summarize these Microsoft Teams conversations for {target_day} in {tz_name}. "
        "Return markdown with sections: Overview, Decisions, Action Items, Risks/Blockers, By Chat. "
        "Be concise, factual, and note when something is unclear.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def summarize_with_openai(target_day: str, chat_messages: Dict[str, List[Dict[str, Any]]], tz_name: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = build_llm_prompt(target_day, chat_messages, tz_name)
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            "input": prompt,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("output_text")


def normalize_messages(messages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for message in messages:
        text = strip_html(message.get("body", {}).get("content", ""))
        if not text:
            continue
        normalized.append(
            {
                "id": message.get("id", ""),
                "createdDateTime": message.get("createdDateTime", ""),
                "sender": message.get("from", {}).get("user", {}).get("displayName", "Unknown"),
                "text": text,
            }
        )

    normalized.sort(key=lambda item: item["createdDateTime"], reverse=True)
    return normalized


def build_report(target_day: str, tz_name: str, chat_messages: Dict[str, List[Dict[str, Any]]], summary_body: str) -> str:
    lines = [
        f"# Teams Daily Summary - {target_day}",
        "",
        f"- Timezone: {tz_name}",
        f"- Chats with activity: {len(chat_messages)}",
        f"- Generated at: {datetime.now().astimezone().isoformat()}",
        "",
        "## Summary",
        "",
        summary_body.strip(),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def output_path_for_day(target_day: str, explicit_path: Optional[str]) -> Path:
    if explicit_path:
        return Path(explicit_path)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"teams_daily_summary_{target_day}.md"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    start_utc, end_utc, _, tz = local_day_bounds(args.date, args.timezone)
    access_token = graph_reader.get_access_token(args)
    chats = list_chats(args, access_token)

    chat_messages: Dict[str, List[Dict[str, Any]]] = {}
    for chat in chats:
        messages = fetch_messages_for_day(args, access_token, chat["id"], start_utc, end_utc)
        normalized = normalize_messages(messages)
        if normalized:
            chat_messages[topic_for_chat(chat)] = normalized

    if not chat_messages:
        body = "No Teams messages were captured for the selected date."
    else:
        body = summarize_with_openai(args.date, chat_messages, args.timezone)
        if not body:
            body = summarize_without_llm(chat_messages, tz)

    report = build_report(args.date, args.timezone, chat_messages, body)
    output_path = output_path_for_day(args.date, args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
