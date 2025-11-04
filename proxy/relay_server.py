#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Relay — Anthropic-compatible SSE → Codex CLI (experimental)
- POST /v1/messages
- POST /v1/messages/count_tokens
- GET  /health
"""
import os, json, time, threading, subprocess, shlex, re
from pathlib import Path
from datetime import datetime
from flask import Flask, request, Response, jsonify

APP = Flask(__name__)

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "proxy_debug.log"

# runtime config via .env
ENV_PATH = ROOT / ".env"
CFG = {
    "CODEX_WORKDIR": "",
    "CODEX_MAX_RUN_SEC": "0",           # 0 = no hard cutoff
    "CODEX_IDLE_AFTER_TURN_SEC": "10",  # idle cutoff after "turn.completed"
    "RELAY_PRETTY_LOG": "1"
}

def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                k,v = line.split("=",1)
                CFG[k.strip()] = v.strip()

load_env()

# simple logger (console + file append)
_lock = threading.Lock()
def log(*a):
    msg = " ".join(str(x) for x in a)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    with _lock:
        print(line, flush=True)
        with LOG_FILE.open("a", encoding="utf-8", errors="replace") as f:
            f.write(line+"\n")

def _parse_cwd_from_prompt(text: str) -> str | None:
    m = re.search(r"Working directory:\s*(.+)", text, flags=re.I)
    if not m: return None
    return m.group(1).strip().strip('"').strip("'")

def _select_cwd(prompt_text: str) -> Path:
    # 1) from user message line
    cand = _parse_cwd_from_prompt(prompt_text or "")
    if cand and Path(cand).exists():
        return Path(cand)
    # 2) from .env
    env_cwd = CFG.get("CODEX_WORKDIR","").strip()
    if env_cwd and Path(env_cwd).exists():
        return Path(env_cwd)
    # 3) current process cwd
    return Path.cwd()

def _iter_sse(items):
    for it in items:
        yield f"event: {it['event']}\n"
        payload = it.get("data", {})
        yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"

def _pretty(msg: str):
    return CFG.get("RELAY_PRETTY_LOG","1") == "1"

@APP.get("/health")
def health():
    return jsonify({
        "ok": True,
        "cwd": str(Path.cwd()),
        "env": CFG,
        "time": datetime.now().isoformat()
    })

@APP.post("/v1/messages/count_tokens")
def count_tokens():
    try:
        body = request.get_json(force=True, silent=True) or {}
        # naive estimate
        text = json.dumps(body, ensure_ascii=False)
        toks = max(32, int(len(text)/4))
        return jsonify({"input_tokens": toks, "output_tokens": 0})
    except Exception as e:
        log("[count_tokens] error:", e)
        return jsonify({"input_tokens": 128, "output_tokens": 0})

@APP.post("/v1/messages")
def messages():
    body = request.get_json(force=True, silent=True) or {}
    # gather content text for CWD detection
    texts = []
    for m in body.get("messages", []):
        c = m.get("content")
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text",""))
    prompt_text = "\n".join(texts)

    workdir = _select_cwd(prompt_text)
    idle_after = max(1, int(CFG.get("CODEX_IDLE_AFTER_TURN_SEC","10") or "10"))
    hard_cut = max(0, int(CFG.get("CODEX_MAX_RUN_SEC","0") or "0"))

    log("(relay) connecting to codex...", "(pretty mode)" if _pretty("") else "(raw)")
    log(f"(relay) using cwd: {workdir}")

    def generate():
        # announce start
        yield from _iter_sse([
            {"event":"message_start", "data":{"type":"message_start","message":{"id":"msg_1","type":"message","role":"assistant"}}},
            {"event":"content_block_start", "data":{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}},
        ])

        # Build codex command
        cmd = ["codex", "exec", "--json", "-","--skip-git-repo-check"]
        log("(relay) spawning:", " ".join(shlex.quote(x) for x in cmd))

        # Join input for codex: pass the plain user text
        codex_input = prompt_text.encode("utf-8", errors="replace")

        try:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=str(workdir), shell=False
            )
        except FileNotFoundError:
            err = "Codex CLI not found. Please `npm i -g @openai/codex` then `codex login`."
            log("(relay) error:", err)
            yield from _iter_sse([
                {"event":"content_block_delta","data":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":err}}},
            ])
            yield from _iter_sse([
                {"event":"content_block_stop","data":{"type":"content_block_stop","index":0}},
                {"event":"message_delta","data":{"type":"message_delta","delta":{},"usage":{"input_tokens":0,"output_tokens":0}}},
                {"event":"message_stop","data":{"type":"message_stop"}},
            ])
            return

        # feed prompt
        try:
            proc.stdin.write(codex_input)
            proc.stdin.close()
        except Exception as e:
            log("(relay) stdin error:", e)

        start = __import__("time").time()
        last_turn_completed = None

        # Streaming stdout lines
        for line in iter(proc.stdout.readline, b""):
            if not line: break
            try:
                s = line.decode("utf-8", "replace").strip()
            except:
                s = line.decode("latin-1","replace").strip()

            if s:
                # try parse codex JSON event then pretty-print a short message
                text_out = s
                try:
                    ev = json.loads(s)
                    if _pretty(""):
                        if ev.get("type") == "item.completed" and isinstance(ev.get("item"), dict):
                            it = ev["item"]
                            if it.get("type") in ("agent_message","reasoning") and isinstance(it.get("text"), str):
                                text_out = it["text"]
                        elif ev.get("type") == "turn.completed":
                            last_turn_completed = __import__("time").time()
                            text_out = "[turn.completed]"
                        else:
                            text_out = ev.get("type","event")
                    else:
                        text_out = s
                except Exception:
                    pass

                yield from _iter_sse([
                    {"event":"content_block_delta","data":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":text_out+"\n"}}},
                ])

            # hard cutoff
            if hard_cut and (__import__("time").time() - start) > hard_cut:
                log("(relay) hard cutoff after", hard_cut, "sec")
                break

            # idle cutoff after turn.completed
            if last_turn_completed and (__import__("time").time() - last_turn_completed) >= idle_after:
                log("(relay) turn completed, idle", idle_after, "sec → close stream.")
                break

        # also forward stderr (last lines) for diagnostics
        tail = proc.stderr.read()
        if tail:
            t = tail.decode("utf-8","replace")[-2000:]
            if t.strip():
                log("(relay) codex stderr tail:", t.strip())
                yield from _iter_sse([
                    {"event":"content_block_delta","data":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"\n[Codex stderr]\n"+t}}},
                ])

        yield from _iter_sse([
            {"event":"content_block_stop","data":{"type":"content_block_stop","index":0}},
            {"event":"message_delta","data":{"type":"message_delta","delta":{},"usage":{"input_tokens":0,"output_tokens":0}}},
            {"event":"message_stop","data":{"type":"message_stop"}},
        ])

    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    log("(relay) Claude Code Relay starting…")
    APP.run(host="0.0.0.0", port=9001, threaded=True)
