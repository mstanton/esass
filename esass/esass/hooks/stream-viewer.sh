#!/bin/bash
#
# ESASS Raw Event Stream Viewer
# =============================
# A simple viewer for Claude Code agent event streams
#
# Usage:
#   ./stream-viewer.sh              # Live stream (default)
#   ./stream-viewer.sh --raw        # Raw JSON output
#   ./stream-viewer.sh --tail 50    # Last 50 events
#   ./stream-viewer.sh --follow     # Follow mode (like tail -f)
#   ./stream-viewer.sh --compact    # Compact single-line format
#   ./stream-viewer.sh --filter Read # Filter by tool name
#

set -e

# ============================================================================
# Configuration
# ============================================================================

ESASS_DATA_DIR="${ESASS_DATA_DIR:-$HOME/.esass/data}"
LOG_DIR="$ESASS_DATA_DIR/logs"
TODAY=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/log_${TODAY}.jsonl"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

# Tool icons (with fallbacks)
declare -A TOOL_ICONS=(
    ["Read"]="[R]"
    ["Write"]="[W]"
    ["Edit"]="[E]"
    ["Bash"]="[$]"
    ["Grep"]="[G]"
    ["Glob"]="[F]"
    ["Task"]="[T]"
    ["WebFetch"]="[U]"
    ["WebSearch"]="[S]"
    ["AskUserQuestion"]="[?]"
)

# Tool colors
declare -A TOOL_COLORS=(
    ["Read"]="$CYAN"
    ["Write"]="$GREEN"
    ["Edit"]="$YELLOW"
    ["Bash"]="$MAGENTA"
    ["Grep"]="$BLUE"
    ["Glob"]="$BLUE"
    ["Task"]="$RED"
    ["WebFetch"]="$WHITE"
    ["WebSearch"]="$WHITE"
)

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "${BOLD}${CYAN}"
    echo "============================================================"
    echo "              ESASS Raw Event Stream Viewer                 "
    echo "============================================================"
    echo -e "${RESET}"
}

print_separator() {
    echo -e "${DIM}────────────────────────────────────────────────────────────${RESET}"
}

# Parse JSON field using grep/sed (no jq dependency)
json_get() {
    local json="$1"
    local field="$2"
    echo "$json" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*: *"\([^"]*\)".*/\1/' | head -1
}

json_get_nested() {
    local json="$1"
    local field="$2"
    # For nested fields like data.tool_name
    echo "$json" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*: *"\([^"]*\)".*/\1/' | head -1
}

# Format a single event line
format_event() {
    local line="$1"
    local mode="$2"

    if [[ "$mode" == "raw" ]]; then
        echo "$line"
        return
    fi

    # Extract fields
    local timestamp=$(json_get "$line" "timestamp")
    local tool_name=$(json_get "$line" "tool_name")
    local category=$(json_get "$line" "category")
    local target=$(json_get "$line" "target")
    local action=$(json_get "$line" "action")

    # Get icon and color
    local icon="${TOOL_ICONS[$tool_name]:-[?]}"
    local color="${TOOL_COLORS[$tool_name]:-$WHITE}"

    # Truncate timestamp to time only
    local time_only="${timestamp:11:8}"

    # Truncate target if too long
    if [[ ${#target} -gt 50 ]]; then
        target="${target:0:47}..."
    fi

    if [[ "$mode" == "compact" ]]; then
        echo -e "${DIM}${time_only}${RESET} ${color}${icon}${RESET} ${BOLD}${tool_name}${RESET} ${target}"
    else
        echo -e "${DIM}[${timestamp}]${RESET}"
        echo -e "  ${color}${icon}${RESET} ${BOLD}${tool_name}${RESET}"
        [[ -n "$category" ]] && echo -e "  ${DIM}Category:${RESET} ${category}"
        [[ -n "$target" ]] && echo -e "  ${DIM}Target:${RESET}   ${target}"
        [[ -n "$action" ]] && echo -e "  ${DIM}Action:${RESET}   ${action}"
        echo ""
    fi
}

# ============================================================================
# Commands
# ============================================================================

cmd_stream() {
    local mode="$1"
    local filter="$2"

    print_header
    echo -e "  Log file: ${CYAN}${LOG_FILE}${RESET}"
    echo -e "  Mode:     ${YELLOW}${mode}${RESET}"
    [[ -n "$filter" ]] && echo -e "  Filter:   ${GREEN}${filter}${RESET}"
    echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop"
    echo ""
    print_separator

    # Create log directory if needed
    mkdir -p "$LOG_DIR"

    # Touch log file if it doesn't exist
    touch "$LOG_FILE"

    # Stream new events
    tail -f "$LOG_FILE" 2>/dev/null | while read -r line; do
        # Apply filter if set
        if [[ -n "$filter" ]]; then
            if ! echo "$line" | grep -q "\"tool_name\"[[:space:]]*:[[:space:]]*\"$filter\""; then
                continue
            fi
        fi

        format_event "$line" "$mode"
    done
}

cmd_tail() {
    local count="$1"
    local mode="$2"
    local filter="$3"

    print_header
    echo -e "  Showing last ${BOLD}${count}${RESET} events"
    [[ -n "$filter" ]] && echo -e "  Filter: ${GREEN}${filter}${RESET}"
    echo ""
    print_separator

    if [[ ! -f "$LOG_FILE" ]]; then
        echo -e "${YELLOW}No events found for today.${RESET}"
        return 1
    fi

    local events
    if [[ -n "$filter" ]]; then
        events=$(grep "\"tool_name\"[[:space:]]*:[[:space:]]*\"$filter\"" "$LOG_FILE" | tail -n "$count")
    else
        events=$(tail -n "$count" "$LOG_FILE")
    fi

    if [[ -z "$events" ]]; then
        echo -e "${YELLOW}No matching events found.${RESET}"
        return 0
    fi

    echo "$events" | while read -r line; do
        format_event "$line" "$mode"
    done
}

cmd_dump() {
    # Dump all raw events from today
    if [[ -f "$LOG_FILE" ]]; then
        cat "$LOG_FILE"
    else
        echo "No events for today" >&2
        return 1
    fi
}

cmd_stats() {
    print_header

    if [[ ! -f "$LOG_FILE" ]]; then
        echo -e "${YELLOW}No events found for today.${RESET}"
        return 1
    fi

    local total=$(wc -l < "$LOG_FILE")
    echo -e "  ${BOLD}Today's Events:${RESET} ${total}"
    echo ""

    echo -e "  ${BOLD}Tool Breakdown:${RESET}"
    grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' "$LOG_FILE" 2>/dev/null | \
        sed 's/.*: *"\([^"]*\)".*/\1/' | \
        sort | uniq -c | sort -rn | \
        while read count tool; do
            local icon="${TOOL_ICONS[$tool]:-[?]}"
            local color="${TOOL_COLORS[$tool]:-$WHITE}"
            printf "    ${color}%s${RESET} %-15s %d\n" "$icon" "$tool" "$count"
        done

    echo ""
    echo -e "  ${BOLD}Categories:${RESET}"
    grep -o '"category"[[:space:]]*:[[:space:]]*"[^"]*"' "$LOG_FILE" 2>/dev/null | \
        sed 's/.*: *"\([^"]*\)".*/\1/' | \
        sort | uniq -c | sort -rn | \
        while read count cat; do
            printf "    %-20s %d\n" "$cat" "$count"
        done
}

cmd_help() {
    echo "ESASS Raw Event Stream Viewer"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  stream, -s        Live stream events (default)"
    echo "  tail, -t N        Show last N events (default: 20)"
    echo "  dump, -d          Dump all raw JSON events"
    echo "  stats             Show event statistics"
    echo "  help, -h          Show this help"
    echo ""
    echo "Options:"
    echo "  --raw, -r         Output raw JSON (no formatting)"
    echo "  --compact, -c     Compact single-line format"
    echo "  --filter, -f X    Filter by tool name (e.g., Read, Edit, Bash)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Live stream with formatting"
    echo "  $0 --raw                # Live stream raw JSON"
    echo "  $0 tail 50              # Last 50 events"
    echo "  $0 tail 20 --compact    # Last 20 in compact mode"
    echo "  $0 --filter Bash        # Only show Bash tool events"
    echo "  $0 dump | jq .          # Pipe raw JSON to jq"
    echo ""
    echo "Environment:"
    echo "  ESASS_DATA_DIR    Data directory (default: ~/.esass/data)"
    echo "  LOG_FILE          Current: $LOG_FILE"
}

# ============================================================================
# Main
# ============================================================================

main() {
    local command="stream"
    local mode="compact"
    local count=20
    local filter=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            stream|-s|--stream)
                command="stream"
                shift
                ;;
            tail|-t|--tail)
                command="tail"
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    count="$2"
                    shift
                fi
                shift
                ;;
            dump|-d|--dump)
                command="dump"
                shift
                ;;
            stats|--stats)
                command="stats"
                shift
                ;;
            help|-h|--help)
                command="help"
                shift
                ;;
            --raw|-r)
                mode="raw"
                shift
                ;;
            --compact|-c)
                mode="compact"
                shift
                ;;
            --full|-f|--verbose|-v)
                mode="full"
                shift
                ;;
            --filter)
                filter="$2"
                shift 2
                ;;
            *)
                # Check if it's a number (for tail)
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    command="tail"
                    count="$1"
                fi
                shift
                ;;
        esac
    done

    # Execute command
    case "$command" in
        stream)
            cmd_stream "$mode" "$filter"
            ;;
        tail)
            cmd_tail "$count" "$mode" "$filter"
            ;;
        dump)
            cmd_dump
            ;;
        stats)
            cmd_stats
            ;;
        help)
            cmd_help
            ;;
        *)
            cmd_help
            return 1
            ;;
    esac
}

main "$@"
