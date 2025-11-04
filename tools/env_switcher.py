#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Relay — ENV Switcher
Switch quickly between: Claude (native) / GLM via z.ai / GPT Code via Relay
"""
import json, sys, urllib.request, urllib.error
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
GLOBAL_SETTINGS_PATH = CLAUDE_DIR / "settings.json"
LOCAL_SETTINGS_PATH = CLAUDE_DIR / "settings.local.json"

def _load(p: Path):
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def _save(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

def _wipe_env(env: dict) -> dict:
    for k in [
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "API_TIMEOUT_MS",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
    ]:
        env.pop(k, None)
    return env

def _write(s: dict, profile: str):
    s.setdefault("meta", {})
    s["meta"]["current_profile"] = profile
    _save(GLOBAL_SETTINGS_PATH, s)
    if LOCAL_SETTINGS_PATH.exists():
        _save(LOCAL_SETTINGS_PATH, s)

def set_claude():
    s = _load(GLOBAL_SETTINGS_PATH)
    env = _wipe_env(s.get("env", {}) if isinstance(s.get("env", {}), dict) else {})
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = "claude-haiku-4-5"
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = "claude-sonnet-4-5"
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"]  = "claude-opus-4-1"
    s["env"] = env
    _write(s, "claude")
    print("✅ Switched to profile: claude")

def set_glm():
    s = _load(GLOBAL_SETTINGS_PATH)
    env = _wipe_env(s.get("env", {}) if isinstance(s.get("env", {}), dict) else {})
    env.update({
        "ANTHROPIC_AUTH_TOKEN":"your_zai_api_key",
        "ANTHROPIC_BASE_URL":"https://api.z.ai/api/anthropic",
        "API_TIMEOUT_MS":"3000000",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL":"glm-4.5-air",
        "ANTHROPIC_DEFAULT_SONNET_MODEL":"glm-4.6",
        "ANTHROPIC_DEFAULT_OPUS_MODEL":"glm-4.6",
    })
    s["env"] = env
    _write(s, "glm_zai")
    print("✅ Switched to profile: glm_zai")

def set_relay(force: bool=False):
    if not force and not _http_ok("http://127.0.0.1:9001/health"):
        print("⚠️ Relay is not running (http://127.0.0.1:9001/health not OK). Use --force to set anyway.")
        return
    s = _load(GLOBAL_SETTINGS_PATH)
    env = _wipe_env(s.get("env", {}) if isinstance(s.get("env", {}), dict) else {})
    env.update({
        "ANTHROPIC_BASE_URL":"http://127.0.0.1:9001",
        "ANTHROPIC_AUTH_TOKEN":"local-dev",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL":"claude-haiku-4-5",
        "ANTHROPIC_DEFAULT_SONNET_MODEL":"claude-sonnet-4-5",
        "ANTHROPIC_DEFAULT_OPUS_MODEL":"claude-opus-4-1",
    })
    s["env"] = env
    _write(s, "gpt_code_via_relay")
    print("✅ Switched to profile: gpt_code_via_relay")

def main(argv):
    if "--claude" in argv: return set_claude()
    if "--glm" in argv: return set_glm()
    if "--relay" in argv:
        return set_relay(force="--force" in argv)
    print("=== Claude Code Relay — ENV Switcher ===")
    print("1) claude (native)")
    print("2) glm_zai (z.ai)")
    print("3) gpt_code_via_relay (experimental)")
    print("0) exit")
    ch = input("Choose: ").strip()
    if ch == "1": set_claude()
    elif ch == "2": set_glm()
    elif ch == "3": set_relay()
    else: print("Bye.")

if __name__ == "__main__":
    main(sys.argv[1:])
