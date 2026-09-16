from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any

import msal
import requests


ROOT = Path(__file__).resolve().parent
CACHE_PATH = ROOT / "token_cache.json"
FLOW_PATH = ROOT / "device_flow.json"
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPES = ["Files.Read.All", "Sites.Read.All"]


def load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text(encoding="utf-8"))
    return cache


def save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")


def build_public_client(cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )


def start_device_flow() -> dict[str, Any]:
    cache = load_cache()
    app = build_public_client(cache)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Microsoft 365 device-code sign-in failed to start: {json.dumps(flow)}")
    FLOW_PATH.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    return flow


def complete_device_flow() -> str:
    if not FLOW_PATH.exists():
        raise RuntimeError("No pending Microsoft 365 device login found. Start device login first.")

    flow = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    cache = load_cache()
    app = build_public_client(cache)
    result = app.acquire_token_by_device_flow(flow)
    save_cache(cache)

    if "access_token" not in result:
        error = result.get("error_description") if result else "unknown error"
        raise RuntimeError(f"Microsoft 365 sign-in failed: {error}")

    return result["access_token"]


def acquire_access_token() -> str:
    cache = load_cache()
    app = build_public_client(cache)

    accounts = app.get_accounts()
    result: dict[str, Any] | None = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        raise RuntimeError("No cached Microsoft 365 sign-in found. Start and complete device login first.")

    return result["access_token"]


def encode_share_url(share_url: str) -> str:
    encoded = base64.urlsafe_b64encode(share_url.encode("utf-8")).decode("ascii")
    encoded = encoded.rstrip("=")
    return f"u!{encoded}"


def graph_get(access_token: str, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        params=params,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def list_folder_children(access_token: str, share_url: str) -> dict[str, Any]:
    share_id = encode_share_url(share_url)
    item = graph_get(
        access_token,
        f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem",
        params={
            "$select": "id,name,webUrl,lastModifiedDateTime,size,folder,file,parentReference"
        },
    )

    children: list[dict[str, Any]] = []
    next_url = f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/children"
    params: dict[str, Any] | None = {
        "$select": "id,name,webUrl,lastModifiedDateTime,size,folder,file,parentReference"
    }

    while next_url:
        payload = graph_get(access_token, next_url, params=params)
        children.extend(payload.get("value", []))
        next_url = payload.get("@odata.nextLink")
        params = None

    return {
        "folder": item,
        "children": children,
    }


def render_markdown(result: dict[str, Any]) -> str:
    folder = result["folder"]
    children = result["children"]

    lines = [
        f"# {folder.get('name', 'Shared Folder')}",
        "",
        f"- URL: {folder.get('webUrl', '')}",
        f"- Item count: {len(children)}",
        "",
        "## Children",
    ]

    if not children:
        lines.append("- No child items found.")
    else:
        for child in children:
            item_type = "folder" if child.get("folder") else "file"
            size = child.get("size", 0)
            modified = child.get("lastModifiedDateTime", "")
            lines.append(
                f"- [{item_type}] {child.get('name', '(unnamed)')} | {size} bytes | {modified} | {child.get('webUrl', '')}"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="List the contents of a shared SharePoint folder.")
    parser.add_argument("--share-url", help="SharePoint sharing URL for a folder.")
    parser.add_argument("--output-root", default=str(ROOT.parent.parent / "sharepoint_search"))
    parser.add_argument("--start-device-login", action="store_true")
    parser.add_argument("--complete-device-login", action="store_true")
    args = parser.parse_args()

    if args.start_device_login:
        flow = start_device_flow()
        print(
            json.dumps(
                {
                    "message": flow["message"],
                    "user_code": flow["user_code"],
                    "verification_uri": flow.get("verification_uri"),
                    "expires_in": flow.get("expires_in"),
                },
                indent=2,
            )
        )
        return 0

    if args.complete_device_login:
        token = complete_device_flow()
        print(json.dumps({"status": "signed_in", "token_prefix": token[:12]}, indent=2))
        return 0

    if not args.share_url:
        raise SystemExit("--share-url is required unless using a device-login mode.")

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    token = acquire_access_token()
    result = list_folder_children(token, args.share_url)

    json_path = output_root / "shared-folder-listing.json"
    md_path = output_root / "shared-folder-listing.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")

    print(
        json.dumps(
            {
                "json_path": str(json_path),
                "markdown_path": str(md_path),
                "item_count": len(result["children"]),
                "folder_name": result["folder"].get("name"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
