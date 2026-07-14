#!/usr/bin/env python3
"""Claim WorkBuddy daily credits through the same API used by the desktop app."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


DEFAULT_ENDPOINT = "https://copilot.tencent.com"
ALLOWED_ENDPOINT_HOSTS = {"copilot.tencent.com"}
STATUS_PATH = "/v2/billing/meter/checkin-activity-status"
CLAIM_PATH = "/v2/billing/meter/daily-checkin"
TIMEOUT_SECONDS = 15
AUTH_GLOB = "Library/Application Support/CodeBuddyExtension/Data/Public/auth/*.info"
LOCK_PATH = Path.home() / ".workbuddy" / "daily-credits.lock"


class ClaimError(RuntimeError):
    def __init__(self, result: str, message: str, exit_code: int = 1):
        super().__init__(message)
        self.result = result
        self.exit_code = exit_code


def candidate_auth_files() -> Iterable[Path]:
    override = os.environ.get("WORKBUDDY_AUTH_FILE")
    if override:
        yield Path(override).expanduser()
    preferred = Path.home() / (
        "Library/Application Support/CodeBuddyExtension/Data/Public/auth/"
        "workbuddy-desktop.info"
    )
    yield preferred
    yield from sorted(Path.home().glob(AUTH_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)


def load_session() -> Tuple[Dict[str, Any], Path]:
    seen = set()
    for path in candidate_auth_files():
        if path in seen:
            continue
        seen.add(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("auth", {}).get("accessToken") and payload.get("account", {}).get("uid"):
                return payload, path
        except (OSError, ValueError, TypeError):
            continue
    raise ClaimError(
        "AUTH_REQUIRED",
        "未找到有效的 WorkBuddy 登录会话；请打开 WorkBuddy 登录后重试。",
        2,
    )


def resolve_endpoint() -> str:
    endpoint = os.environ.get("WORKBUDDY_API_BASE", DEFAULT_ENDPOINT).rstrip("/")
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_ENDPOINT_HOSTS:
        raise ClaimError(
            "UNSAFE_ENDPOINT",
            "拒绝向非 WorkBuddy HTTPS 域名发送登录凭证。",
            5,
        )
    return endpoint


def headers_for(session: Dict[str, Any]) -> Dict[str, str]:
    account = session["account"]
    auth = session["auth"]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth['accessToken']}",
        "X-User-Id": str(account["uid"]),
        "User-Agent": "WorkBuddy-Daily-Credits/1.0",
    }
    enterprise_id = account.get("enterpriseId")
    if enterprise_id:
        headers["X-Enterprise-Id"] = str(enterprise_id)
        headers["X-Tenant-Id"] = str(enterprise_id)
    if auth.get("domain"):
        headers["X-Domain"] = str(auth["domain"])
    return headers


def post_json(endpoint: str, path: str, headers: Dict[str, str]) -> Dict[str, Any]:
    request = urllib.request.Request(
        endpoint + path,
        data=b"{}",
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise ClaimError(
                "AUTH_REQUIRED",
                "WorkBuddy 登录已失效；请打开 WorkBuddy 刷新登录后重试。",
                2,
            ) from None
        raise ClaimError("HTTP_ERROR", f"WorkBuddy 接口返回 HTTP {error.code}。", 3) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise ClaimError("NETWORK_ERROR", f"网络请求失败：{reason}", 3) from None
    except (ValueError, TypeError):
        raise ClaimError("INVALID_RESPONSE", "WorkBuddy 接口返回了无法解析的数据。", 3) from None

    if not isinstance(payload, dict):
        raise ClaimError("INVALID_RESPONSE", "WorkBuddy 接口返回格式异常。", 3)
    return payload


def extract_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("code") != 0:
        message = str(payload.get("msg") or "WorkBuddy 接口请求失败")
        raise ClaimError("API_ERROR", message, 4)
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ClaimError("INVALID_RESPONSE", "WorkBuddy 接口缺少 data 字段。", 3)
    return data


def compact_status(data: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "active",
        "today_checked_in",
        "today_credit",
        "daily_credit",
        "streak_days",
        "total_credits",
        "end_time",
    )
    return {key: data[key] for key in keys if key in data}


def compact_claim(data: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "credit",
        "credits",
        "today_credit",
        "streak_days",
        "total_credits",
        "message",
    )
    return {key: data[key] for key in keys if key in data}


def run(status_only: bool) -> Dict[str, Any]:
    session, _ = load_session()
    endpoint = resolve_endpoint()
    headers = headers_for(session)
    status = extract_data(post_json(endpoint, STATUS_PATH, headers))

    if status_only:
        return {"result": "STATUS", **compact_status(status)}
    if not status.get("active", False):
        return {"result": "INACTIVE", **compact_status(status)}
    if status.get("today_checked_in", False):
        return {"result": "ALREADY_CLAIMED", **compact_status(status)}

    try:
        claim = extract_data(post_json(endpoint, CLAIM_PATH, headers))
    except ClaimError as error:
        # A concurrent client may have claimed between the status and claim calls.
        refreshed = extract_data(post_json(endpoint, STATUS_PATH, headers))
        if refreshed.get("today_checked_in", False):
            return {"result": "ALREADY_CLAIMED", **compact_status(refreshed)}
        raise error

    verified = extract_data(post_json(endpoint, STATUS_PATH, headers))
    if not verified.get("today_checked_in", False):
        raise ClaimError("VERIFY_FAILED", "领取接口返回成功，但状态复核未通过。", 4)
    return {
        "result": "CLAIMED",
        **compact_claim(claim),
        **compact_status(verified),
    }


def render(result: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return
    code = result.get("result")
    if code == "CLAIMED":
        amount = result.get("credit", result.get("credits", result.get("today_credit", "?")))
        print(f"领取成功：+{amount} WorkBuddy 积分")
    elif code == "ALREADY_CLAIMED":
        print("今日积分已领取")
    elif code == "INACTIVE":
        print("当前没有可领取的每日积分活动")
    else:
        print(json.dumps(result, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claim WorkBuddy daily credits without a model call.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="Only inspect today's claim status.")
    mode.add_argument("--claim", action="store_true", help="Claim when available (default).")
    parser.add_argument("--json", action="store_true", help="Emit one compact JSON line.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            render({"result": "ALREADY_RUNNING"}, args.json)
            return 0
        try:
            render(run(status_only=args.status), args.json)
            return 0
        except ClaimError as error:
            render({"result": error.result, "message": str(error)}, args.json)
            return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
