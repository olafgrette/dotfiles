#!/bin/bash
# Starship-inspired status line for Claude Code
# Palette: bg_mid=#394260, bg_dark=#1d2230, accent=#769ff0, muted=#a3aed2

input=$(cat)

# --- Colors (24-bit ANSI) ---
BG_MID='\e[48;2;57;66;96m'    # #394260
BG_DARK='\e[48;2;29;34;48m'   # #1d2230
FG_ACCENT='\e[38;2;118;159;240m'   # #769ff0
FG_MUTED='\e[38;2;163;174;210m'   # #a3aed2
FG_ORANGE='\e[38;2;255;153;51m'   # orange for input tokens
FG_GREEN='\e[38;2;152;195;121m'   # #98c379 for model
FG_GOLD='\e[38;2;212;175;55m'    # #d4af37 for cost
FG_WHITE='\e[38;2;220;220;220m'
RESET='\e[0m'

# --- OS icon ---
os_icon=""
case "$(uname -s)" in
  Darwin) os_icon="";;
  Linux)
    if [ -f /etc/os-release ] && grep -qi "arch" /etc/os-release 2>/dev/null; then
      os_icon=""
    else
      os_icon="🐧"
    fi
    ;;
esac

# --- Hostname (truncated at first '.') ---
host=$(hostname)
host="${host%%.*}"

# --- Session name ---
session_name=$(echo "$input" | jq -r '.session_name // empty')

# --- CWD (replace $HOME with ~) ---
cwd="${PWD/#$HOME/~}"

# --- Model ---
model=$(echo "$input" | jq -r '.model.display_name // empty')

# --- Context used % ---
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
ctx_display=""
if [ -n "$used_pct" ]; then
  used_int=$(printf '%.0f' "$used_pct")
  ctx_display="ctx:${used_int}%"
fi

# --- Token formatter: 1234 → 1.2k, 1234567 → 1.2M ---
fmt_tokens() {
  local n="$1"
  if [ -z "$n" ] || [ "$n" = "null" ]; then echo ""; return; fi
  if [ "$n" -ge 1000000 ]; then
    printf "%.1fM" "$(echo "scale=2; $n / 1000000" | bc)"
  elif [ "$n" -ge 1000 ]; then
    printf "%.1fk" "$(echo "scale=2; $n / 1000" | bc)"
  else
    printf "%d" "$n"
  fi
}

cost=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
cost_display=""
if [ -n "$cost" ]; then
  cost_display=$(printf '$%.2f' "$cost")
fi

api_ms=$(echo "$input" | jq -r '.cost.total_api_duration_ms // empty')
api_display=""
if [ -n "$api_ms" ]; then
  api_s=$((api_ms / 1000))
  api_m=$((api_s / 60))
  api_s=$((api_s % 60))
  if [ "$api_m" -gt 0 ]; then
    api_display="${api_m}m${api_s}s"
  else
    api_display="${api_s}s"
  fi
fi

rate_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
rate_display=""
if [ -n "$rate_pct" ]; then
  rate_display="rl:${rate_pct}%"
fi

total_in=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
total_out=$(echo "$input" | jq -r '.context_window.total_output_tokens // empty')
in_fmt=$(fmt_tokens "$total_in")
out_fmt=$(fmt_tokens "$total_out")

# --- Assemble ---
# Segment 1 (bg_mid): OS icon + session name + hostname
printf "${BG_MID}${FG_WHITE} ${os_icon} "

if [ -n "$session_name" ]; then
  printf "${FG_ACCENT}${session_name}${FG_MUTED}@${FG_ACCENT}${host} "
else
  printf "${FG_MUTED}${host} "
fi

# CWD (same bg_mid segment)
printf "${FG_WHITE}${cwd} "

# Segment 2 (bg_dark): model + context % + tokens
printf "${BG_DARK} "

if [ -n "$model" ]; then
  printf "${FG_GREEN}${model} "
fi

if [ -n "$ctx_display" ]; then
  printf "${FG_MUTED}%s " "${ctx_display}"
fi

if [ -n "$in_fmt" ]; then
  printf "${FG_ORANGE}↑${in_fmt} "
fi

if [ -n "$out_fmt" ]; then
  printf "${FG_ACCENT}↓${out_fmt} "
fi

if [ -n "$rate_display" ]; then
  printf "${FG_MUTED}%s " "${rate_display}"
fi

if [ -n "$cost_display" ]; then
  printf "${FG_GOLD}%s " "${cost_display}"
fi

if [ -n "$api_display" ]; then
  printf "${FG_MUTED}%s " "${api_display}"
fi

printf "${RESET}"
