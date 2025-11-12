from __future__ import annotations
import json, os, urllib.request


def send_slack(webhook_url: str, text: str):
    data = {"text": text}
    req = urllib.request.Request(webhook_url, data=json.dumps(data).encode("utf-8"),
                                 headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()

def send_alert(summary: str, details=None):
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat  = os.getenv("TELEGRAM_CHAT_ID")
    slack    = os.getenv("SLACK_WEBHOOK_URL")
    body = summary
    if details:
        try:
            body += "\n" + json.dumps(details, ensure_ascii=False)[:3500]
        except Exception:
            pass
    if slack:
        try: send_slack(slack, body)
        except Exception as e: print("[alerts] slack failed:", e)
