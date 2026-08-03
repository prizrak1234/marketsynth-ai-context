#!/usr/bin/env python3
"""API smoke for chat golden path — general_answer via mock LLM."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from uuid import uuid4

BASE = "http://127.0.0.1:8000"
EMAIL = sys.argv[1] if len(sys.argv) > 1 else "chat-golden-path-dev@marketsynth.test"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "ChatGoldenPathDev2026!"
QUESTION = (
    "Что такое unit-экономика SaaS и как её считать для подписной модели?"
)


def _post_json(path: str, payload: dict, opener: urllib.request.OpenerDirector) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": "http://localhost:3000"},
        method="POST",
    )
    with opener.open(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    login = _post_json(
        "/auth/login",
        {"email": EMAIL, "password": PASSWORD},
        opener,
    )
    print("login_ok", login.get("user", {}).get("email"))

    client_id = str(uuid4())
    body = _post_json(
        "/user-requests",
        {
            "text": QUESTION,
            "client_message_id": client_id,
            "idempotency_key": f"chat-smoke-{client_id}",
        },
        opener,
    )
    print("chat_route", body.get("chat_route"))
    print("status", body.get("status"))
    print("execution_provider", body.get("execution_provider"))
    print("llm_calls", (body.get("skill_inputs") or {}).get("_llm_call_count"))
    assistant = body.get("assistant_message") or ""
    print("assistant_prefix", assistant[:120])
    if body.get("chat_route") != "general_answer":
        raise SystemExit("FAIL: expected chat_route=general_answer")
    if "Для SaaS обычно нужен устойчивый проект" in assistant:
        raise SystemExit("FAIL: stale SaaS canned stub")
    if "Marketsynth (mock)" not in assistant and body.get("execution_provider") != "mock":
        raise SystemExit("FAIL: expected mock general_answer response")
    print("smoke_ok")


if __name__ == "__main__":
    main()
