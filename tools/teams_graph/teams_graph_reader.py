import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read Teams chats and messages through Microsoft Graph. "
            "This script only works with an IT-approved Entra app and Graph permissions."
        )
    )
    parser.add_argument(
        "--auth-mode",
        choices=["device_code", "client_credentials"],
        default=os.getenv("MS_AUTH_MODE", "device_code"),
        help="Authentication flow. Use device_code for your own account, or client_credentials for an approved service app.",
    )
    parser.add_argument(
        "--tenant-id",
        default=os.getenv("MS_TENANT_ID"),
        help="Microsoft Entra tenant ID. Can also be set through MS_TENANT_ID.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("MS_CLIENT_ID"),
        help="App registration client ID. Can also be set through MS_CLIENT_ID.",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("MS_CLIENT_SECRET"),
        help="Client secret for client_credentials mode. Can also be set through MS_CLIENT_SECRET.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("MS_USER_ID"),
        help="Required for client_credentials list-chats mode. Can also be set through MS_USER_ID.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of chats or messages to request.",
    )
    parser.add_argument(
        "--output",
        choices=["json", "table"],
        default="table",
        help="Output format.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-chats", help="List chats available to the authenticated user or target user.")

    messages_parser = subparsers.add_parser("list-messages", help="List messages from a specific chat.")
    messages_parser.add_argument("--chat-id", required=True, help="Teams chat ID.")

    return parser


def require(value: Optional[str], name: str) -> str:
    if value:
        return value
    raise SystemExit(f"Missing required value: {name}")


def token_url(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


def device_code_url(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"


def get_device_code_token(tenant_id: str, client_id: str) -> str:
    scope = "Chat.Read User.Read offline_access openid profile"
    response = requests.post(
        device_code_url(tenant_id),
        data={"client_id": client_id, "scope": scope},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    print(payload["message"], file=sys.stderr)

    expires_at = time.time() + int(payload.get("expires_in", 900))
    interval = int(payload.get("interval", 5))

    while time.time() < expires_at:
        poll = requests.post(
            token_url(tenant_id),
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": payload["device_code"],
            },
            timeout=30,
        )

        if poll.status_code == 200:
            return poll.json()["access_token"]

        error_payload = poll.json()
        error = error_payload.get("error")
        if error in {"authorization_pending", "slow_down"}:
            time.sleep(interval + (5 if error == "slow_down" else 0))
            continue

        raise RuntimeError(
            f"Device code sign-in failed: {error_payload.get('error_description', error)}"
        )

    raise RuntimeError("Timed out waiting for device code sign-in.")


def get_client_credentials_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    response = requests.post(
        token_url(tenant_id),
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_access_token(args: argparse.Namespace) -> str:
    tenant_id = require(args.tenant_id, "tenant ID")
    client_id = require(args.client_id, "client ID")

    if args.auth_mode == "device_code":
        return get_device_code_token(tenant_id, client_id)

    client_secret = require(args.client_secret, "client secret")
    return get_client_credentials_token(tenant_id, client_id, client_secret)


def graph_get(access_token: str, path: str, query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{GRAPH_BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def list_chats(args: argparse.Namespace, access_token: str) -> Dict[str, Any]:
    query = {"$top": args.top}
    if args.auth_mode == "device_code":
        return graph_get(access_token, "/me/chats", query=query)

    user_id = require(args.user_id, "user ID for client_credentials mode")
    return graph_get(access_token, f"/users/{user_id}/chats", query=query)


def list_messages(args: argparse.Namespace, access_token: str) -> Dict[str, Any]:
    query = {"$top": args.top}
    if args.auth_mode == "device_code":
        return graph_get(access_token, f"/me/chats/{args.chat_id}/messages", query=query)

    return graph_get(access_token, f"/chats/{args.chat_id}/messages", query=query)


def print_table(payload: Dict[str, Any], command: str) -> None:
    rows = payload.get("value", [])
    if command == "list-chats":
        for item in rows:
            chat_id = item.get("id", "")
            chat_type = item.get("chatType", "")
            topic = item.get("topic") or ""
            web_url = item.get("webUrl") or ""
            print(f"{chat_id}\t{chat_type}\t{topic}\t{web_url}")
        return

    for item in rows:
        created = item.get("createdDateTime", "")
        from_user = (
            item.get("from", {})
            .get("user", {})
            .get("displayName", "")
        )
        body = item.get("body", {}).get("content", "")
        print(f"{created}\t{from_user}\t{body}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        access_token = get_access_token(args)
        if args.command == "list-chats":
            payload = list_chats(args, access_token)
        else:
            payload = list_messages(args, access_token)
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(f"HTTP error: {detail}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print_table(payload, args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
