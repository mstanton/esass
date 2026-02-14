# ESASS Enhancement Plan: Hardening & Intelligence

This document outlines the technical implementation plan for the next phase of the **Evolutionary Self-Accelerating Skill System (ESASS)**.

---

## 1. Architectural Hardening (Reliability & Performance)

*Goal: Move from prototype-grade file persistence to a robust, scalable data layer.*

### 1.1 sqlite3 Integration

- **Rationale**: Currently, ESASS uses `JSONL` for logs and `pickle` for probe state. This is prone to race conditions and corruption when monitored in real-time.
- **Action**: Implement a `DatabasePipeline` in `esass/probes/pipeline.py` that utilizes an SQLite backend.
- **Fields**: Events, Session ID, Timestamp, Event Type, and JSON data blobs.

### 1.2 Configurable Protection Zones

- **Rationale**: `FieldBoundaryProbe` currently has hardcoded paths for "Core" and "Trusted" zones.
- **Action**: Create a `.esass.json` support in the project root to define:

  ```json
  {
    "zones": {
      "CORE": ["pyproject.toml", ".env", "config/"],
      "TRUSTED": ["src/", "tests/"]
    }
  }
  ```

### 1.3 Log Rotation & Retention

- **Rationale**: Prevent `~/.esass/data` from growing unbounded.
- **Action**: Add a background cleanup task to the Hook that prunes logs older than 7 days or exceeds 1GB.

---

## 2. Real-time Observation (Agent Intelligence)

*Goal: Enhance the system's ability to sense-make and detect agent inefficiencies.*

### 2.1 Latency Monitoring Probe

- **Action**: Create `LatencyProbe` to track the delta between `tool_call_start` and `tool_call_complete`.
- **Visualization**: Display average tool response times in the Dashboard gauges.

### 2.2 Semantic Anomaly Detection (Logic Loops)

- **Action**: Implement detection for "Self-Correction Loops"—where an agent repeatedly toggles the same code block or runs the same failing command with no variation.
- **Alert**: Trigger a `LOGIC_LOOP` reliability alert if a pattern repeats >3 times.

### 2.3 Causality & Task Trees

- **Action**: Use the `parent_event_id` and `context` stacks to build a relational graph of tool calls.
- **Benefit**: Understanding *why* an agent is grepping (e.g., as a result of a failed read) allows for better "Drift" assessment.

---

## 3. Dashboard & Monitoring UX (The Control Center)

*Goal: Transform the dashboard into an interactive, high-fidelity monitoring environment.*

### 3.1 Interactive TUI (Keyboard Shortcuts)

- **Action**: Implement non-blocking keyboard input using `msvcrt` (Windows) or `select` (Unix).
- **Controls**:
  - `[H]` Toggle visibility of historical alerts.
  - `[S]` Save current dashboard "snapshot" to a Markdown report.
  - `[C]` Clear event buffer.

### 3.2 Trend Graphing (Sparklines)

- **Action**: Implement lightweight ASCII sparklines to show:
  - Error frequency over the last 15 minutes.
  - Success rate trends.
- **Library**: Custom Unicode-based horizontal bar charts.

### 3.3 Enhanced Alert Highlighting

- **Action**: Use flashing ANSI sequences or distinct background colors for critical boundary violations (e.g., unauthorized `Edit` on a `CORE` file).

---

## Implementation Roadmap

1. [ ] **Phase 1**: SQLite Migration (Foundation).
2. [ ] **Phase 2**: Latency & Loop Detection Probes.
3. [ ] **Phase 3**: Interactive Dashboard UX & Trends.
