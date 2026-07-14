#!/bin/bash
# llama-common.sh — shared helpers for gemma-serve / qwen-* serve scripts.
# Source via: source "$HOME/.local/lib/llama-common.sh"
#
# Why: three serve scripts shared ~80% logic (mode parsing, cache, server
# lookup, platform offload). This file centralizes it and fixes two bugs:
# - unsafe SERVER_BIN=$(... || echo llama-server) fallback (gemma/precise)
# - OFFLOAD_NOTE unbound on Darwin under set -u (precise)

# Cache location, overridable via env
export LLAMA_CACHE="${LLAMA_CACHE:-$HOME/.model-cache}"

# Always initialize to avoid unbound variable under set -u
OFFLOAD_NOTE=""

# Parse first arg as MODE if it is coding|general|no-think.
# Sets global MODE, and returns 0 if first arg was a mode (caller should shift),
# 1 otherwise (flag or no arg). Also validates unknown positionals.
# Usage:
#   llama_parse_mode "$@"
#   if [ "$_llama_mode_consumed" = 1 ]; then shift; fi
_llama_mode_consumed=0
MODE="general"

llama_parse_mode() {
    MODE="general"
    _llama_mode_consumed=0
    if [ $# -gt 0 ]; then
        case "$1" in
            coding|general|no-think)
                MODE="$1"
                _llama_mode_consumed=1
                ;;
            -*)
                # flag, keep default mode
                ;;
            *)
                echo "Usage: $0 [coding|general|no-think] [server options...]" >&2
                exit 1
                ;;
        esac
    fi
}

# Safe server bin lookup — replaces unsafe `|| echo llama-server` pattern.
llama_find_server() {
    local bin
    bin=$(command -v llama-server-cuda 2>/dev/null || command -v llama-server 2>/dev/null || true)
    if [ -z "$bin" ]; then
        echo "Error: llama-server-cuda or llama-server not found in PATH" >&2
        exit 1
    fi
    printf '%s' "$bin"
}

# Common platform args: --no-mmproj-offload on Linux (VRAM scarce), not on
# Darwin (unified Metal, no separate VRAM). Caller may append more.
llama_init_platform() {
    PLATFORM_ARGS=()
    OFFLOAD_NOTE=""
    if [ "$(uname)" != "Darwin" ]; then
        PLATFORM_ARGS+=(--no-mmproj-offload)
    fi
}

# Mode -> TEMP/TOP_P override helper
# Sets TEMP and optionally TOP_P based on MODE. Caller sets defaults before.
llama_apply_mode_temps() {
    case "$MODE" in
        coding)
            TEMP=0.6
            ;;
        general)
            TEMP=1.0
            ;;
        no-think)
            TEMP=0.7
            TOP_P=0.8
            EXTRA_ARGS+=(--chat-template-kwargs '{"enable_thinking":false}')
            ;;
    esac
}
