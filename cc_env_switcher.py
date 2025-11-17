#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Claude Code Relay — Environment Switcher (root version)"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Tuple

HOME = Path.home()
CWD = Path.cwd()

GLOBAL_SETTINGS_PATH = HOME / '.claude' / 'settings.json'
GLOBAL_LOCAL_SETTINGS_PATH = HOME / '.claude' / 'settings.local.json'
PROJECT_SETTINGS_PATH = CWD / '.claude' / 'settings.json'
PROJECT_LOCAL_SETTINGS_PATH = CWD / '.claude' / 'settings.local.json'

SETTINGS_CANDIDATES: List[Path] = [
    PROJECT_LOCAL_SETTINGS_PATH,
    PROJECT_SETTINGS_PATH,
    GLOBAL_LOCAL_SETTINGS_PATH,
    GLOBAL_SETTINGS_PATH,
]


def _load(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save(p: Path, d: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _wipe_env(env: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(env, dict):
        return {}
    keys_to_clear = [
        'ANTHROPIC_AUTH_TOKEN',
        'ANTHROPIC_BASE_URL',
        'API_TIMEOUT_MS',
        'ANTHROPIC_DEFAULT_HAIKU_MODEL',
        'ANTHROPIC_DEFAULT_SONNET_MODEL',
        'ANTHROPIC_DEFAULT_OPUS_MODEL',
        'ZAI_API_KEY',
        'GLM_API_KEY',
        'CLAUDE_CODE_API_KEY_HELPER_COMMAND',
        'CLAUDE_CODE_API_KEY_HELPER_TTL_MS',
    ]
    for k in keys_to_clear:
        env.pop(k, None)
    return env


def _apply_profile(
    profile_name: str,
    mode: str,
    *,
    force_relay: bool = False,
    extra_env: Dict[str, str] | None = None,
) -> None:
    if mode == 'relay' and not force_relay:
        if not _http_ok('http://127.0.0.1:9001/health'):
            print('⚠️ Relay is not running (http://127.0.0.1:9001/health not OK). Use --force with --relay to ignore this check.')
            return

    updated_paths: List[Path] = []
    targets = [p for p in SETTINGS_CANDIDATES if p.exists()]
    if not targets:
        targets = [GLOBAL_SETTINGS_PATH]

    for path in targets:
        cfg = _load(path)
        env = cfg.get('env', {})
        if not isinstance(env, dict):
            env = {}

        env = _wipe_env(env)
        if extra_env:
            env.update(extra_env)

        if mode == 'claude':
            env.setdefault('ANTHROPIC_DEFAULT_HAIKU_MODEL', 'claude-haiku-4-5')
            env.setdefault('ANTHROPIC_DEFAULT_SONNET_MODEL', 'claude-sonnet-4-5')
            env.setdefault('ANTHROPIC_DEFAULT_OPUS_MODEL', 'claude-opus-4-1')

        elif mode == 'glm':
            src_extra = extra_env or {}
            key = (
                src_extra.get('ZAI_API_KEY')
                or src_extra.get('GLM_API_KEY')
                or env.get('ZAI_API_KEY')
                or env.get('GLM_API_KEY')
                or os.environ.get('ZAI_API_KEY')
                or os.environ.get('GLM_API_KEY')
            )
            if not key:
                key = 'your_zai_api_key_here'
            env.update({
                'ANTHROPIC_AUTH_TOKEN': key,
                'ANTHROPIC_BASE_URL': 'https://api.z.ai/api/anthropic',
                'API_TIMEOUT_MS': '3000000',
                'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'glm-4.5-air',
                'ANTHROPIC_DEFAULT_SONNET_MODEL': 'glm-4.6',
                'ANTHROPIC_DEFAULT_OPUS_MODEL': 'glm-4.6',
            })

        elif mode == 'relay':
            env.update({
                'ANTHROPIC_BASE_URL': 'http://127.0.0.1:9001',
                'ANTHROPIC_AUTH_TOKEN': 'local-dev',
                'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'claude-haiku-4-5',
                'ANTHROPIC_DEFAULT_SONNET_MODEL': 'claude-sonnet-4-5',
                'ANTHROPIC_DEFAULT_OPUS_MODEL': 'claude-opus-4-1',
            })
        else:
            raise ValueError(f'Unknown mode: {mode!r}')

        cfg['env'] = env
        meta = cfg.get('meta') or {}
        meta['current_profile'] = profile_name
        cfg['meta'] = meta
        _save(path, cfg)
        updated_paths.append(path)

    print(f'✅ Switched to profile: {profile_name}')
    print('   Updated settings files:')
    for p in updated_paths:
        print(f'   • {p}')


def set_claude(extra_env: Dict[str, str] | None = None) -> None:
    _apply_profile('claude', mode='claude', extra_env=extra_env)


def set_glm(extra_env: Dict[str, str] | None = None) -> None:
    _apply_profile('glm_zai', mode='glm', extra_env=extra_env)


def set_relay(*, force: bool = False, extra_env: Dict[str, str] | None = None) -> None:
    _apply_profile('gpt_code_via_relay', mode='relay', force_relay=force, extra_env=extra_env)


def _parse_env_args(argv: List[str]) -> Tuple[List[str], Dict[str, str]]:
    clean: List[str] = []
    extra: Dict[str, str] = {}
    i = 0
    n = len(argv)
    while i < n:
        token = argv[i]
        if token == '--env':
            i += 1
            while i < n and not argv[i].startswith('--'):
                pair = argv[i]
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k:
                        extra[k] = v
                i += 1
        else:
            clean.append(token)
            i += 1
    return clean, extra


def main(argv: List[str]) -> None:
    argv = list(argv)
    argv, extra_env = _parse_env_args(argv)

    if '--help' in argv or '-h' in argv:
        print('Usage:')
        print('  python cc_env_switcher.py --claude')
        print('  python cc_env_switcher.py --glm [--env ZAI_API_KEY=sk-xxx]')
        print('  python cc_env_switcher.py --relay [--force]')
        return

    if '--claude' in argv:
        set_claude(extra_env=extra_env or None)
        return

    if '--glm' in argv:
        set_glm(extra_env=extra_env or None)
        return

    if '--relay' in argv:
        force = '--force' in argv
        set_relay(force=force, extra_env=extra_env or None)
        return

    print('=== Claude Code Relay — ENV Switcher ===')
    print('1) claude (native subscription)')
    print('2) glm_zai (z.ai)')
    print('3) gpt_code_via_relay (experimental)')
    print('0) exit')
    choice = input('Choose: ').strip()
    if choice == '1':
        set_claude(extra_env=extra_env or None)
    elif choice == '2':
        set_glm(extra_env=extra_env or None)
    elif choice == '3':
        set_relay(force=False, extra_env=extra_env or None)
    else:
        print('Bye.')


if __name__ == '__main__':
    main(sys.argv[1:])
