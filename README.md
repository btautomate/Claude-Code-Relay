# Claude Code Relay

A small toolkit that lets **Claude Code (Anthropic CLI)** quickly switch environments and optionally talk to
**OpenAI Codex CLI (GPT Code)** through an **Anthropic-compatible proxy**. In addition to the experimental
**GPT Code** path, the toolkit includes two stable modes: **Claude (native)** and **GLM via z.ai**.

> ⚠️ **Experimental**: the **GPT Code / Codex CLI** path may be limited by vendor changes and may break without notice.
> Recommended for **POC/Debug** only — **not** for production workloads.

---

## 1) Architecture

```
                 ┌──────────────────────────────────────────────────────┐
                 │                    Claude Code (CLI)                 │
                 │  reads ~/.claude/settings.json → env (models/routes) │
                 └───────────────┬──────────────────────────────────────┘
                                 │
             ┌───────────────────┼─────────────────────┐
             │                   │                     │
     (A) Claude Native     (B) GLM via z.ai      (C) GPT Code via Relay (experimental)
     ─────────────────      ───────────────      ───────────────────────────────────────
   ANTHROPIC_BASE_URL     ANTHROPIC_BASE_URL     ANTHROPIC_BASE_URL → http://127.0.0.1:9001
   unset (Anthropic)      https://api.z.ai/...   ANTHROPIC_AUTH_TOKEN → local-dev
   tokens: Anthropic      tokens: z.ai key       Claude → Relay (SSE) → Codex CLI (subprocess)
   API: /v1/messages      API: /v1/messages      Relay emits SSE: message_start/delta/stop
                                                Health: GET /health, Logs: proxy_debug.log
```

**Components**

- `tools/env_switcher.py` — **ENV switcher** (claude / glm_zai / gpt_code_via_relay).
- `proxy/relay_server.py` — **Relay** (Flask + SSE) that shells out to Codex CLI via `subprocess`.
- `.env.example` — config for `CODEX_WORKDIR`, `CODEX_MAX_RUN_SEC`, `CODEX_IDLE_AFTER_TURN_SEC`.
- `examples/request.json` — Anthropic-like request payload for testing.

---

## 2) Tech & Decisions

- **Python 3.10+**
- **Flask** to expose endpoints:
  - `POST /v1/messages` — SSE streaming (Anthropic-compatible).
  - `POST /v1/messages/count_tokens` — mock token counter so the Claude UI does not crash.
  - `GET /health` — report status & runtime config.
- **Subprocess Codex CLI** (`codex exec --json -`) instead of Realtime WS (public models lack realtime support).
- **CWD** chosen in this order:
  1. A line in the user message: `Working directory: D:\...`
  2. `.env` variable `CODEX_WORKDIR`
  3. The current process CWD (where you run the relay)
- **Logging**: console + file `proxy_debug.log` (append mode).
- **Windows-friendly**: advise `chcp 65001` or `PYTHONIOENCODING=utf-8` if emoji logs cause encoding errors.

---

## 3) Installation

### 3.1 Codex CLI (only if using GPT Code)
```powershell
npm i -g @openai/codex
codex login
```

### 3.2 Switch profile with the ENV Switcher
```powershell
python tools/env_switcher.py
# 1) claude   2) glm_zai   3) gpt_code_via_relay
```
> The switcher **auto-GETs** `http://127.0.0.1:9001/health`; it only sets the relay profile if the relay is running.
> (Use `--force` to set the relay profile anyway.)

---

## 4) Run the Relay (GPT Code path)

```powershell
copy .env.example .env
# Edit .env if needed:
# CODEX_WORKDIR=D:\Works\Bitbucket\your-repo
# CODEX_MAX_RUN_SEC=0            # 0 = no hard cutoff; rely on idle-after-turn
# CODEX_IDLE_AFTER_TURN_SEC=10   # seconds to close stream after turn.completed

python proxy/relay_server.py

# Health check
curl http://127.0.0.1:9001/health
```

Open a real repo (e.g., `D:\Works\Bitbucket\my-repo`), run `claude`, and type **hi** to test.  
Want to pin CWD per session? Add this line in the first prompt:
`Working directory: D:\\Works\\Bitbucket\\my-repo`

---

## 5) Troubleshooting

- **Claude UI “undefined is not an object (H.map)”**: the SSE stream is missing fields or wrong order — compare raw SSE in `proxy_debug.log`.
- **UnicodeEncodeError (emoji)**: use `chcp 65001` / `PYTHONIOENCODING=utf-8` or remove emojis in your app’s logger.
- **Not inside a trusted directory**: relay passes `--skip-git-repo-check` to Codex; ensure the CLI has sufficient rights.
- **Hangs**: verify CWD exists, adjust `CODEX_MAX_RUN_SEC`, and check if `turn.completed` was seen (relay closes after idle).

---

## 6) Layout

```
claude-code-relay-en/
├─ proxy/
│  └─ relay_server.py
├─ tools/
│  └─ env_switcher.py
├─ examples/
│  └─ request.json
├─ .env.example
├─ LICENSE
└─ README.md
```

---

## 7) License

MIT © 2025 BT Automate
