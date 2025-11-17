# Claude Code Relay — Enhanced Version with Environment Switcher

This repository provides a development relay and environment switcher for **Claude Code**, allowing you to seamlessly switch between:

- **Claude (native subscription mode — no API key needed)**
- **GLM (z.ai — Anthropic-compatible API)**
- **Local GPT-Code Relay (localhost:9001)**

The project now includes:
- A **robust environment switching tool** `cc_env_switcher.py`
- Full **support for inline API key usage** (`--env KEY=value`)
- Automatic cleaning of invalid Anthropic env variables
- Enhanced instructions and usage examples

---

# 📌 1. Features

### ✅ Switch between 3 model providers
| Mode | Description |
|------|-------------|
| `--claude` | Use Claude subscription (NO API KEY required) |
| `--glm` | Use GLM (z.ai) via compatible Anthropic API |
| `--relay` | Use local GPT-Code relay at `http://127.0.0.1:9001` |

### ✅ No leftover variables
When switching back to Claude subscription mode, script auto-removes:

- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_BASE_URL`
- `API_TIMEOUT_MS`
- Old GLM/proxy variables

### ✅ Multiple key input methods
- Via OS environment variables (`ZAI_API_KEY`, `GLM_API_KEY`)
- Via inline CLI arguments (`--env KEY=value`)
- Via manual edit in `.claude/settings.json`

---

# 📌 2. Installation

Clone or unzip into your workspace:

```bash
git clone https://github.com/your-name/claude-code-relay-en.git
cd claude-code-relay-en
```

Make sure Python 3.8+ is installed.

---

# 📌 3. How the Switching System Works

Claude Code reads configuration from FOUR layers (highest priority first):

| Priority | File location | Description |
|---------|----------------|-------------|
| 1 | `.claude/settings.local.json` | Project-local override |
| 2 | `.claude/settings.json` | Project config |
| 3 | `~/.claude/settings.local.json` | User-local override |
| 4 | `~/.claude/settings.json` | User-global default |

The switcher automatically updates **all relevant files**.

If none exist, it automatically creates:

```text
~/.claude/settings.json
```

---

# 📌 4. Usage Guide — Switching Commands

All commands below should be run **from the repository root**:

```bash
cd claude-code-relay-en
python cc_env_switcher.py ...
```

## 🟦 A. Switch to Claude Subscription Mode (NO API KEY)

```bash
python cc_env_switcher.py --claude
```

This will:

- Remove all GLM/proxy variables
- Ensure no `ANTHROPIC_BASE_URL` or `ANTHROPIC_AUTH_TOKEN` is set
- Restore `ANTHROPIC_DEFAULT_*` model fields

> 💡 **Use this whenever you return from GLM → Claude**

---

## 🟨 B. Switch to GLM (z.ai)

### **Option A — Inline Key (recommended for 1-time use)**

```bash
python cc_env_switcher.py --glm --env ZAI_API_KEY=sk-your-glm-key
```

Supports multiple keys:

```bash
python cc_env_switcher.py --glm --env ZAI_API_KEY=sk-key GLM_API_KEY=backup-key
```

### **Option B — Environment Variable**

**PowerShell (Windows):**

```powershell
$env:ZAI_API_KEY="sk-your-glm-key"
python cc_env_switcher.py --glm
```

**Linux/macOS (bash):**

```bash
export ZAI_API_KEY="sk-your-glm-key"
python cc_env_switcher.py --glm
```

### **Option C — Manual edit**

After running:

```bash
python cc_env_switcher.py --glm
```

Open the generated file (for example):

```text
~/.claude/settings.json
```

Replace:

```jsonc
"ANTHROPIC_AUTH_TOKEN": "your_zai_api_key_here"
```

with your real GLM key.

---

## 🟥 C. Switch to Local GPT-Code Relay

```bash
python cc_env_switcher.py --relay
```

If relay is not running → script warns.

To force-enable:

```bash
python cc_env_switcher.py --relay --force
```

Relay expected at:

```text
http://127.0.0.1:9001
```

---

# 📌 5. Full CLI Reference

| Command | Description |
|--------|-------------|
| `--claude` | Use Claude subscription mode |
| `--glm` | Switch to GLM (z.ai) |
| `--relay` | Use local GPT Code relay |
| `--force` | Skip health check for relay |
| `--env KEY=value` | Provide inline environment values |
| `--help` | Show help |

### Examples

Switch to GLM with inline key:

```bash
python cc_env_switcher.py --glm --env ZAI_API_KEY=sk-123
```

Switch to relay & skip health check:

```bash
python cc_env_switcher.py --relay --force
```

Interactive mode:

```bash
python cc_env_switcher.py
```

---

# 📌 6. Fix: API Key Errors When Returning to Claude

If you see errors such as:

```text
API key invalid
```

or:

```text
Unauthorized
```

Run:

```bash
python cc_env_switcher.py --claude
```

Additionally, check Windows environment variables:

```powershell
Get-ChildItem Env:ANTHROPIC*
```

Delete problematic ones:

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $null, "User")
```

Then restart your terminal / VS Code.

---

# 📌 7. Folder Structure

```text
claude-code-relay-en/
 ├── proxy/                 # Relay implementation
 ├── tools/                 # Additional helper tools
 ├── cc_env_switcher.py     # NEW: environment profile switcher
 ├── README.md              # This file
 ├── LICENSE
 └── examples/              # Example configs / usage
```

---

# 📌 8. Credits

Enhanced by **BT Automate** with support for:

- Inline environment injection
- Automatic cleanup of Anthropic overrides
- Multi-profile switching system
- Improved README documentation
