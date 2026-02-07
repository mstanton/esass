#!/usr/bin/env python3
"""
ESASS Hook for Claude Code

Captures tool calls from Claude Code and logs them to ESASS.
Configure in ~/.claude/hooks.json to enable automatic observation.

Setup:
    Add to ~/.claude/hooks.json:
    {
      "hooks": {
        "PostToolUse": [{
          "command": "python /path/to/esass_hook.py",
          "timeout": 5000
        }]
      }
    }
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import hashlib

# ESASS data directory
ESASS_DATA_DIR = Path(os.environ.get(
    'ESASS_DATA_DIR',
    Path.home() / '.esass' / 'data'
))

def ensure_data_dir():
    """Ensure data directory exists."""
    ESASS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (ESASS_DATA_DIR / 'logs').mkdir(exist_ok=True)
    (ESASS_DATA_DIR / 'state').mkdir(exist_ok=True)
    (ESASS_DATA_DIR / 'patterns').mkdir(exist_ok=True)
    (ESASS_DATA_DIR / 'skills').mkdir(exist_ok=True)

def get_session_id():
    """Get or create today's session ID."""
    state_file = ESASS_DATA_DIR / 'state' / 'current_session.json'
    today = datetime.now().strftime('%Y%m%d')

    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                if state.get('date') == today:
                    return state.get('session_id')
        except:
            pass

    # Create new session
    session_id = f"session_{today}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
    ensure_data_dir()
    with open(state_file, 'w') as f:
        json.dump({'date': today, 'session_id': session_id}, f)

    return session_id

def extract_context(tool_name: str, params: dict) -> dict:
    """Extract semantic context from tool call."""
    context = {
        'category': 'unknown',
        'target': None,
        'action': None,
        'tags': []
    }

    # Categorize by tool
    if tool_name in ['Read', 'Write', 'Edit']:
        context['category'] = 'file_operation'
        context['target'] = params.get('file_path', '')
        context['action'] = tool_name.lower()

        # Extract file type
        if context['target']:
            ext = Path(context['target']).suffix.lower()
            if ext:
                context['tags'].append(f"filetype:{ext}")

            # Detect common patterns
            path_lower = context['target'].lower()
            if 'test' in path_lower:
                context['tags'].append('testing')
            if 'config' in path_lower or ext in ['.json', '.yaml', '.yml', '.toml']:
                context['tags'].append('configuration')
            if '__init__' in path_lower:
                context['tags'].append('module_init')

    elif tool_name in ['Grep', 'Glob']:
        context['category'] = 'search'
        context['action'] = 'search'
        context['target'] = params.get('pattern', params.get('query', ''))
        context['tags'].append('codebase_exploration')

    elif tool_name == 'Bash':
        context['category'] = 'command'
        cmd = params.get('command', '')
        context['target'] = cmd[:100]

        # Detect command types
        if cmd.startswith('git '):
            context['tags'].append('git')
            if 'commit' in cmd:
                context['action'] = 'commit'
            elif 'push' in cmd:
                context['action'] = 'push'
            elif 'pull' in cmd or 'fetch' in cmd:
                context['action'] = 'sync'
            elif 'status' in cmd or 'diff' in cmd or 'log' in cmd:
                context['action'] = 'inspect'
        elif cmd.startswith('pytest') or cmd.startswith('python -m pytest'):
            context['tags'].append('testing')
            context['action'] = 'test'
        elif cmd.startswith('pip ') or cmd.startswith('npm '):
            context['tags'].append('package_management')
            context['action'] = 'install' if 'install' in cmd else 'package_op'
        elif 'docker' in cmd:
            context['tags'].append('containerization')

    elif tool_name == 'Task':
        context['category'] = 'delegation'
        context['action'] = 'spawn_agent'
        context['target'] = params.get('subagent_type', 'unknown')
        context['tags'].append(f"agent:{context['target']}")

    elif tool_name in ['WebFetch', 'WebSearch']:
        context['category'] = 'web'
        context['action'] = 'fetch' if tool_name == 'WebFetch' else 'search'
        context['target'] = params.get('url', params.get('query', ''))
        context['tags'].append('external_resource')

    return context

def log_event(event_type: str, data: dict):
    """Append event to daily log file."""
    ensure_data_dir()

    today = datetime.now().strftime('%Y%m%d')
    log_file = ESASS_DATA_DIR / 'logs' / f'log_{today}.jsonl'

    entry = {
        'id': hashlib.md5(f"{datetime.now().isoformat()}{event_type}{json.dumps(data)}".encode()).hexdigest()[:16],
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'session_id': get_session_id(),
        'data': data
    }

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')

    return entry['id']

def update_sequence_state(tool_name: str, context: dict):
    """Track tool sequences for pattern detection."""
    state_file = ESASS_DATA_DIR / 'state' / 'sequence_state.json'

    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {'recent_tools': [], 'sequences': {}}

        # Add to recent tools (keep last 10)
        state['recent_tools'].append({
            'tool': tool_name,
            'category': context['category'],
            'timestamp': datetime.now().isoformat()
        })
        state['recent_tools'] = state['recent_tools'][-10:]

        # Track 2-tool and 3-tool sequences
        tools = [t['tool'] for t in state['recent_tools']]
        if len(tools) >= 2:
            seq2 = f"{tools[-2]} -> {tools[-1]}"
            state['sequences'][seq2] = state['sequences'].get(seq2, 0) + 1
        if len(tools) >= 3:
            seq3 = f"{tools[-3]} -> {tools[-2]} -> {tools[-1]}"
            state['sequences'][seq3] = state['sequences'].get(seq3, 0) + 1

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    except Exception:
        pass  # Don't fail on state tracking errors

def main():
    """Process hook input from Claude Code."""
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return

        hook_data = json.loads(input_data)

        # Extract fields from Claude Code hook
        tool_name = hook_data.get('tool_name', 'unknown')
        tool_input = hook_data.get('tool_input', {})
        tool_output = hook_data.get('tool_output', '')
        session_id = hook_data.get('session_id', 'unknown')

        # Skip if tool name looks invalid
        if not tool_name or tool_name == 'unknown':
            return

        # Extract semantic context
        context = extract_context(tool_name, tool_input)

        # Prepare log data
        log_data = {
            'tool_name': tool_name,
            'parameters': tool_input,
            'result_preview': str(tool_output)[:500] if tool_output else None,
            'context': context,
            'original_session': session_id
        }

        # Log the event
        log_event('tool_call', log_data)

        # Update sequence tracking
        update_sequence_state(tool_name, context)

    except json.JSONDecodeError:
        # Not valid JSON
        pass
    except Exception as e:
        # Log errors for debugging
        try:
            log_event('hook_error', {'error': str(e)})
        except:
            pass

if __name__ == '__main__':
    main()
