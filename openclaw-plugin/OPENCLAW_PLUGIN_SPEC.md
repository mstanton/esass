# OpenClaw Plugin Specification: ESASS Integration

## Plugin: `@esass/openclaw-plugin`

**Version**: 1.0.0  
**Type**: Observation & Learning Plugin  
**Category**: Meta-Cognitive Extension  
**Compatibility**: OpenClaw ≥0.5.0

---

## Overview

This specification defines the `@esass/openclaw-plugin` - a plugin that integrates the Emergent Self-Adaptive Skill System (ESASS) with the OpenClaw daemon (`openclawd`). The plugin observes agent execution, detects behavioral patterns, and generates new skills that feed back into the OpenClaw ecosystem.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENCLAWD PLUGIN ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          OPENCLAWD CORE                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ Gateway  │  │  Agent   │  │  Tools   │  │ Channels │            │   │
│  │  │ Server   │  │  Loop    │  │ Executor │  │ Manager  │            │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │       │             │             │             │                   │   │
│  │       └─────────────┴─────────────┴─────────────┘                   │   │
│  │                           │                                         │   │
│  │                    Plugin Event Bus                                 │   │
│  │                           │                                         │   │
│  └───────────────────────────┼─────────────────────────────────────────┘   │
│                              │                                             │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    @esass/openclaw-plugin                            │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │   Observer   │  │   Pattern    │  │    Skill     │              │   │
│  │  │    Hooks     │  │   Detector   │  │  Publisher   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Manifest

### `package.json`

```json
{
  "name": "@esass/openclaw-plugin",
  "version": "1.0.0",
  "description": "ESASS meta-cognitive learning plugin for OpenClaw",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "openclaw": {
    "type": "plugin",
    "name": "esass",
    "displayName": "ESASS Learning Engine",
    "description": "Emergent Self-Adaptive Skill System - Learn from agent behavior",
    "category": "observation",
    "icon": "brain",
    "minVersion": "0.5.0",
    "permissions": [
      "agent:observe",
      "tools:observe",
      "skills:write",
      "storage:read",
      "storage:write",
      "network:clawhub"
    ],
    "hooks": [
      "agent:beforeExecute",
      "agent:afterExecute",
      "agent:onThinking",
      "tools:beforeCall",
      "tools:afterCall",
      "tools:onError",
      "skills:onActivate",
      "skills:onComplete",
      "session:onStart",
      "session:onEnd"
    ],
    "configSchema": "./config.schema.json",
    "commands": [
      {
        "name": "esass:status",
        "description": "Show ESASS learning status"
      },
      {
        "name": "esass:patterns",
        "description": "List detected patterns"
      },
      {
        "name": "esass:skills",
        "description": "List generated skills"
      },
      {
        "name": "esass:cycle",
        "description": "Trigger learning cycle manually"
      }
    ]
  },
  "dependencies": {
    "@openclaw/plugin-sdk": "^0.5.0"
  },
  "peerDependencies": {
    "openclaw": ">=0.5.0"
  }
}
```

---

## Plugin Interface

### Core Plugin Class

```typescript
import {
  OpenClawPlugin,
  PluginContext,
  PluginConfig,
  HookHandler,
  EventEmitter
} from '@openclaw/plugin-sdk';

/**
 * ESASS OpenClaw Plugin
 * 
 * Integrates the Emergent Self-Adaptive Skill System with OpenClaw,
 * enabling automatic skill learning from agent behavior.
 */
export default class ESASSPlugin implements OpenClawPlugin {
  
  /** Plugin metadata */
  static readonly id = 'esass';
  static readonly version = '1.0.0';
  static readonly displayName = 'ESASS Learning Engine';
  
  /** Plugin state */
  private context: PluginContext;
  private config: ESASSPluginConfig;
  private observer: ESASSObserver;
  private detector: PatternDetector;
  private publisher: SkillPublisher;
  private loopController: LoopController;
  
  /**
   * Called when plugin is loaded
   */
  async onLoad(context: PluginContext): Promise<void> {
    this.context = context;
    this.config = await this.loadConfig();
    
    context.logger.info('ESASS plugin loading...');
    
    // Initialize components
    this.observer = new ESASSObserver(this.config.observation);
    this.detector = new PatternDetector(this.config.detection);
    this.publisher = new SkillPublisher(this.config.publishing);
    this.loopController = new LoopController(this.config.loop);
    
    context.logger.info('ESASS plugin loaded');
  }
  
  /**
   * Called when plugin is enabled
   */
  async onEnable(): Promise<void> {
    this.context.logger.info('ESASS plugin enabling...');
    
    // Register hooks
    this.registerHooks();
    
    // Start learning loop if auto-start enabled
    if (this.config.loop.autoStart) {
      await this.loopController.start();
    }
    
    // Register commands
    this.registerCommands();
    
    this.context.logger.info('ESASS plugin enabled');
  }
  
  /**
   * Called when plugin is disabled
   */
  async onDisable(): Promise<void> {
    this.context.logger.info('ESASS plugin disabling...');
    
    // Stop learning loop
    await this.loopController.stop();
    
    // Flush pending observations
    await this.observer.flush();
    
    // Unregister hooks
    this.unregisterHooks();
    
    this.context.logger.info('ESASS plugin disabled');
  }
  
  /**
   * Called when plugin is unloaded
   */
  async onUnload(): Promise<void> {
    this.context.logger.info('ESASS plugin unloading...');
    
    // Cleanup resources
    await this.observer.shutdown();
    await this.detector.shutdown();
    await this.publisher.shutdown();
    
    this.context.logger.info('ESASS plugin unloaded');
  }
  
  /**
   * Handle configuration changes
   */
  async onConfigChange(newConfig: Partial<ESASSPluginConfig>): Promise<void> {
    this.config = { ...this.config, ...newConfig };
    
    // Propagate config changes
    this.observer.updateConfig(this.config.observation);
    this.detector.updateConfig(this.config.detection);
    this.publisher.updateConfig(this.config.publishing);
    this.loopController.updateConfig(this.config.loop);
  }
  
  /**
   * Register event hooks
   */
  private registerHooks(): void {
    const hooks = this.context.hooks;
    
    // Session lifecycle
    hooks.on('session:onStart', this.handleSessionStart.bind(this));
    hooks.on('session:onEnd', this.handleSessionEnd.bind(this));
    
    // Agent execution
    hooks.on('agent:onThinking', this.handleThinking.bind(this));
    hooks.on('agent:beforeExecute', this.handleBeforeExecute.bind(this));
    hooks.on('agent:afterExecute', this.handleAfterExecute.bind(this));
    
    // Tool execution
    hooks.on('tools:beforeCall', this.handleToolStart.bind(this));
    hooks.on('tools:afterCall', this.handleToolComplete.bind(this));
    hooks.on('tools:onError', this.handleToolError.bind(this));
    
    // Skill usage
    hooks.on('skills:onActivate', this.handleSkillActivate.bind(this));
    hooks.on('skills:onComplete', this.handleSkillComplete.bind(this));
  }
  
  /**
   * Unregister event hooks
   */
  private unregisterHooks(): void {
    const hooks = this.context.hooks;
    
    hooks.off('session:onStart', this.handleSessionStart);
    hooks.off('session:onEnd', this.handleSessionEnd);
    hooks.off('agent:onThinking', this.handleThinking);
    hooks.off('agent:beforeExecute', this.handleBeforeExecute);
    hooks.off('agent:afterExecute', this.handleAfterExecute);
    hooks.off('tools:beforeCall', this.handleToolStart);
    hooks.off('tools:afterCall', this.handleToolComplete);
    hooks.off('tools:onError', this.handleToolError);
    hooks.off('skills:onActivate', this.handleSkillActivate);
    hooks.off('skills:onComplete', this.handleSkillComplete);
  }
  
  /**
   * Register plugin commands
   */
  private registerCommands(): void {
    const commands = this.context.commands;
    
    commands.register('esass:status', this.cmdStatus.bind(this));
    commands.register('esass:patterns', this.cmdPatterns.bind(this));
    commands.register('esass:skills', this.cmdSkills.bind(this));
    commands.register('esass:cycle', this.cmdCycle.bind(this));
  }
}
```

---

## Hook Specifications

### Session Hooks

#### `session:onStart`

Fired when a new conversation session begins.

```typescript
interface SessionStartEvent {
  sessionId: string;
  channel: ChannelType;
  userId?: string;
  metadata: Record<string, unknown>;
  timestamp: Date;
}

async handleSessionStart(event: SessionStartEvent): Promise<void> {
  await this.observer.startSession({
    sessionId: event.sessionId,
    channel: event.channel,
    userId: event.userId,
    startTime: event.timestamp
  });
}
```

#### `session:onEnd`

Fired when a conversation session ends.

```typescript
interface SessionEndEvent {
  sessionId: string;
  reason: 'completed' | 'timeout' | 'error' | 'user_ended';
  duration: number;
  messageCount: number;
  timestamp: Date;
}

async handleSessionEnd(event: SessionEndEvent): Promise<void> {
  await this.observer.endSession({
    sessionId: event.sessionId,
    reason: event.reason,
    duration: event.duration,
    messageCount: event.messageCount,
    endTime: event.timestamp
  });
}
```

---

### Agent Hooks

#### `agent:onThinking`

Fired when the agent produces a thinking/reasoning block.

```typescript
interface ThinkingEvent {
  sessionId: string;
  content: string;
  thinkingType: 'planning' | 'analysis' | 'decision' | 'reflection';
  tokenCount: number;
  timestamp: Date;
}

async handleThinking(event: ThinkingEvent): Promise<void> {
  await this.observer.observeThinking({
    sessionId: event.sessionId,
    content: event.content,
    type: event.thinkingType,
    timestamp: event.timestamp
  });
}
```

#### `agent:beforeExecute`

Fired before the agent executes an action.

```typescript
interface BeforeExecuteEvent {
  sessionId: string;
  action: AgentAction;
  context: ExecutionContext;
  timestamp: Date;
}

async handleBeforeExecute(event: BeforeExecuteEvent): Promise<void> {
  await this.observer.observeActionStart({
    sessionId: event.sessionId,
    actionType: event.action.type,
    actionData: event.action.data,
    context: event.context,
    timestamp: event.timestamp
  });
}
```

#### `agent:afterExecute`

Fired after the agent completes an action.

```typescript
interface AfterExecuteEvent {
  sessionId: string;
  action: AgentAction;
  result: ActionResult;
  duration: number;
  timestamp: Date;
}

async handleAfterExecute(event: AfterExecuteEvent): Promise<void> {
  await this.observer.observeActionComplete({
    sessionId: event.sessionId,
    actionType: event.action.type,
    result: event.result,
    success: event.result.success,
    duration: event.duration,
    timestamp: event.timestamp
  });
}
```

---

### Tool Hooks

#### `tools:beforeCall`

Fired before a tool is invoked.

```typescript
interface ToolCallStartEvent {
  sessionId: string;
  callId: string;
  toolName: string;
  parameters: Record<string, unknown>;
  causedBy?: string;  // Parent call ID for nested calls
  timestamp: Date;
}

async handleToolStart(event: ToolCallStartEvent): Promise<void> {
  await this.observer.observeToolStart({
    sessionId: event.sessionId,
    callId: event.callId,
    toolName: event.toolName,
    parameters: this.sanitizeParameters(event.parameters),
    causedBy: event.causedBy,
    timestamp: event.timestamp
  });
}
```

#### `tools:afterCall`

Fired after a tool completes successfully.

```typescript
interface ToolCallCompleteEvent {
  sessionId: string;
  callId: string;
  toolName: string;
  result: unknown;
  resultSize: number;
  duration: number;
  timestamp: Date;
}

async handleToolComplete(event: ToolCallCompleteEvent): Promise<void> {
  await this.observer.observeToolComplete({
    sessionId: event.sessionId,
    callId: event.callId,
    toolName: event.toolName,
    success: true,
    resultSummary: this.summarizeResult(event.result),
    duration: event.duration,
    timestamp: event.timestamp
  });
}
```

#### `tools:onError`

Fired when a tool execution fails.

```typescript
interface ToolCallErrorEvent {
  sessionId: string;
  callId: string;
  toolName: string;
  error: Error;
  errorType: string;
  recoverable: boolean;
  timestamp: Date;
}

async handleToolError(event: ToolCallErrorEvent): Promise<void> {
  await this.observer.observeToolError({
    sessionId: event.sessionId,
    callId: event.callId,
    toolName: event.toolName,
    errorType: event.errorType,
    errorMessage: event.error.message,
    recoverable: event.recoverable,
    timestamp: event.timestamp
  });
}
```

---

### Skill Hooks

#### `skills:onActivate`

Fired when a skill is activated.

```typescript
interface SkillActivateEvent {
  sessionId: string;
  skillId: string;
  skillName: string;
  skillVersion: string;
  trigger: string;
  triggerConfidence: number;
  context: SkillContext;
  timestamp: Date;
}

async handleSkillActivate(event: SkillActivateEvent): Promise<void> {
  await this.observer.observeSkillActivation({
    sessionId: event.sessionId,
    skillId: event.skillId,
    skillName: event.skillName,
    version: event.skillVersion,
    trigger: event.trigger,
    confidence: event.triggerConfidence,
    timestamp: event.timestamp
  });
  
  // Track for feedback loop
  this.publisher.trackActivation(event.skillId, event.sessionId);
}
```

#### `skills:onComplete`

Fired when a skill execution completes.

```typescript
interface SkillCompleteEvent {
  sessionId: string;
  skillId: string;
  skillName: string;
  success: boolean;
  outcome: SkillOutcome;
  duration: number;
  toolsUsed: string[];
  timestamp: Date;
}

async handleSkillComplete(event: SkillCompleteEvent): Promise<void> {
  await this.observer.observeSkillCompletion({
    sessionId: event.sessionId,
    skillId: event.skillId,
    skillName: event.skillName,
    success: event.success,
    outcome: event.outcome,
    duration: event.duration,
    toolsUsed: event.toolsUsed,
    timestamp: event.timestamp
  });
  
  // Update feedback metrics
  this.publisher.recordOutcome(event.skillId, event.success);
}
```

---

## Configuration Schema

### `config.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "ESASS Plugin Configuration",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": true,
      "description": "Enable/disable the ESASS plugin"
    },
    "observation": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable event observation"
        },
        "dataDir": {
          "type": "string",
          "default": "~/.openclaw/esass/data",
          "description": "Directory for observation data"
        },
        "sampleRate": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "default": 1.0,
          "description": "Event sampling rate (1.0 = all events)"
        },
        "bufferSize": {
          "type": "integer",
          "minimum": 10,
          "maximum": 1000,
          "default": 100,
          "description": "Event buffer size before flush"
        },
        "flushInterval": {
          "type": "integer",
          "minimum": 1000,
          "maximum": 60000,
          "default": 5000,
          "description": "Flush interval in milliseconds"
        },
        "probes": {
          "type": "object",
          "properties": {
            "toolProbe": {
              "type": "boolean",
              "default": true
            },
            "reasoningProbe": {
              "type": "boolean",
              "default": true
            },
            "decisionProbe": {
              "type": "boolean",
              "default": true
            },
            "skillProbe": {
              "type": "boolean",
              "default": true
            }
          }
        },
        "sanitization": {
          "type": "object",
          "properties": {
            "removeSecrets": {
              "type": "boolean",
              "default": true
            },
            "truncateLargeValues": {
              "type": "boolean",
              "default": true
            },
            "maxValueLength": {
              "type": "integer",
              "default": 1000
            }
          }
        }
      }
    },
    "detection": {
      "type": "object",
      "properties": {
        "minSupport": {
          "type": "integer",
          "minimum": 1,
          "default": 10,
          "description": "Minimum pattern occurrences"
        },
        "minConfidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "default": 0.8,
          "description": "Minimum pattern confidence"
        },
        "minStabilityDays": {
          "type": "integer",
          "minimum": 1,
          "default": 7,
          "description": "Minimum pattern stability in days"
        },
        "maxSequenceLength": {
          "type": "integer",
          "minimum": 2,
          "maximum": 10,
          "default": 5,
          "description": "Maximum pattern sequence length"
        },
        "maxGapSeconds": {
          "type": "integer",
          "minimum": 60,
          "default": 300,
          "description": "Maximum gap between sequence events"
        }
      }
    },
    "publishing": {
      "type": "object",
      "properties": {
        "autoPublish": {
          "type": "boolean",
          "default": false,
          "description": "Automatically publish skills to ClawHub"
        },
        "confidenceThreshold": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "default": 0.85,
          "description": "Minimum confidence for auto-publish"
        },
        "supportThreshold": {
          "type": "integer",
          "minimum": 1,
          "default": 15,
          "description": "Minimum support for auto-publish"
        },
        "requireApproval": {
          "type": "boolean",
          "default": true,
          "description": "Require human approval before publish"
        },
        "clawHub": {
          "type": "object",
          "properties": {
            "registry": {
              "type": "string",
              "default": "https://clawhub.com"
            },
            "token": {
              "type": "string",
              "description": "ClawHub API token"
            },
            "defaultTags": {
              "type": "array",
              "items": { "type": "string" },
              "default": ["esass-generated"]
            }
          }
        },
        "localSkillsDir": {
          "type": "string",
          "default": "~/.openclaw/skills/esass-generated",
          "description": "Directory for locally generated skills"
        }
      }
    },
    "loop": {
      "type": "object",
      "properties": {
        "autoStart": {
          "type": "boolean",
          "default": true,
          "description": "Auto-start learning loop on plugin enable"
        },
        "observationWindowHours": {
          "type": "integer",
          "minimum": 1,
          "default": 24,
          "description": "Hours of logs to analyze per cycle"
        },
        "cycleIntervalHours": {
          "type": "integer",
          "minimum": 1,
          "default": 6,
          "description": "Hours between learning cycles"
        },
        "minEventsForDetection": {
          "type": "integer",
          "minimum": 10,
          "default": 100,
          "description": "Minimum events before running detection"
        },
        "maxSkillsPerCycle": {
          "type": "integer",
          "minimum": 1,
          "default": 5,
          "description": "Maximum skills to generate per cycle"
        },
        "rateLimitPerDay": {
          "type": "integer",
          "minimum": 1,
          "default": 10,
          "description": "Maximum skills to publish per day"
        }
      }
    },
    "evolution": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable skill evolution system"
        },
        "similarityThreshold": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "default": 0.8,
          "description": "Threshold for skill unification"
        },
        "deprecationGraceDays": {
          "type": "integer",
          "minimum": 1,
          "default": 30,
          "description": "Grace period before deprecating skills"
        },
        "maxEvolutionsPerDay": {
          "type": "integer",
          "minimum": 1,
          "default": 3,
          "description": "Maximum skill evolutions per day"
        }
      }
    }
  },
  "required": []
}
```

---

## Default Configuration

### `esass.config.yaml`

```yaml
# ESASS OpenClaw Plugin Configuration
# Location: ~/.openclaw/plugins/esass/config.yaml

enabled: true

observation:
  enabled: true
  dataDir: ~/.openclaw/esass/data
  sampleRate: 1.0
  bufferSize: 100
  flushInterval: 5000
  
  probes:
    toolProbe: true
    reasoningProbe: true
    decisionProbe: true
    skillProbe: true
  
  sanitization:
    removeSecrets: true
    truncateLargeValues: true
    maxValueLength: 1000

detection:
  minSupport: 10
  minConfidence: 0.8
  minStabilityDays: 7
  maxSequenceLength: 5
  maxGapSeconds: 300

publishing:
  autoPublish: false  # Disabled by default for safety
  confidenceThreshold: 0.85
  supportThreshold: 15
  requireApproval: true
  
  clawHub:
    registry: https://clawhub.com
    # token: set via CLAWHUB_TOKEN env var
    defaultTags:
      - esass-generated
      - auto-learned
  
  localSkillsDir: ~/.openclaw/skills/esass-generated

loop:
  autoStart: true
  observationWindowHours: 24
  cycleIntervalHours: 6
  minEventsForDetection: 100
  maxSkillsPerCycle: 5
  rateLimitPerDay: 10

evolution:
  enabled: true
  similarityThreshold: 0.8
  deprecationGraceDays: 30
  maxEvolutionsPerDay: 3
```

---

## Plugin Commands

### `esass:status`

Display current ESASS learning status.

```typescript
interface StatusCommand {
  name: 'esass:status';
  description: 'Show ESASS learning status';
  options: {
    verbose?: boolean;
    json?: boolean;
  };
}

async cmdStatus(options: StatusOptions): Promise<CommandResult> {
  const status = {
    enabled: this.config.enabled,
    loopRunning: this.loopController.isRunning(),
    currentPhase: this.loopController.getPhase(),
    
    metrics: {
      eventsObserved: this.observer.getTotalEvents(),
      sessionsTracked: this.observer.getTotalSessions(),
      patternsDetected: this.detector.getTotalPatterns(),
      skillCandidates: this.detector.getCandidateCount(),
      skillsGenerated: this.publisher.getGeneratedCount(),
      skillsPublished: this.publisher.getPublishedCount()
    },
    
    lastCycle: {
      timestamp: this.loopController.getLastCycleTime(),
      duration: this.loopController.getLastCycleDuration(),
      results: this.loopController.getLastCycleResults()
    },
    
    nextCycle: this.loopController.getNextCycleTime()
  };
  
  if (options.json) {
    return { output: JSON.stringify(status, null, 2) };
  }
  
  return { output: this.formatStatus(status) };
}
```

**Example Output:**

```
ESASS Learning Status
═════════════════════

Status: ✓ Enabled and Running
Phase:  Observing

Metrics:
  Events Observed:    2,450
  Sessions Tracked:   156
  Patterns Detected:  32
  Skill Candidates:   12
  Skills Generated:   8
  Skills Published:   6

Last Cycle:
  Time:     2026-02-01 15:30:00 (45 min ago)
  Duration: 12.4 seconds
  Patterns: 5 detected, 2 candidates
  Skills:   1 generated

Next Cycle: 2026-02-01 21:30:00 (5h 15m)
```

---

### `esass:patterns`

List detected behavioral patterns.

```typescript
interface PatternsCommand {
  name: 'esass:patterns';
  description: 'List detected patterns';
  options: {
    candidates?: boolean;  // Only show skill candidates
    limit?: number;        // Max patterns to show
    sort?: 'support' | 'confidence' | 'recent';
    json?: boolean;
  };
}

async cmdPatterns(options: PatternsOptions): Promise<CommandResult> {
  let patterns = await this.detector.getPatterns();
  
  if (options.candidates) {
    patterns = patterns.filter(p => p.skillCandidate);
  }
  
  // Sort patterns
  patterns = this.sortPatterns(patterns, options.sort || 'support');
  
  // Apply limit
  if (options.limit) {
    patterns = patterns.slice(0, options.limit);
  }
  
  if (options.json) {
    return { output: JSON.stringify(patterns, null, 2) };
  }
  
  return { output: this.formatPatterns(patterns) };
}
```

**Example Output:**

```
Detected Patterns (32 total, 12 candidates)
═══════════════════════════════════════════

✓ CANDIDATE: git-workflow-pattern
  Sequence:  reasoning:git → tool:Bash:git* → decision:commit
  Support:   45 occurrences
  Confidence: 94%
  Stability: 12 days
  First Seen: 2026-01-15

✓ CANDIDATE: code-analysis-pattern
  Sequence:  tool:Glob → tool:Read → reasoning:analysis
  Support:   38 occurrences
  Confidence: 87%
  Stability: 10 days
  First Seen: 2026-01-18

○ EMERGING: test-debug-pattern
  Sequence:  tool:Bash:pytest → reasoning:debug → tool:Edit
  Support:   8 occurrences (need 10)
  Confidence: 82%
  Stability: 5 days
  First Seen: 2026-01-27

[Use --candidates to show only skill candidates]
[Use --json for machine-readable output]
```

---

### `esass:skills`

List generated skills.

```typescript
interface SkillsCommand {
  name: 'esass:skills';
  description: 'List generated skills';
  options: {
    status?: 'pending' | 'published' | 'all';
    limit?: number;
    json?: boolean;
  };
}

async cmdSkills(options: SkillsOptions): Promise<CommandResult> {
  let skills = await this.publisher.getGeneratedSkills();
  
  if (options.status && options.status !== 'all') {
    skills = skills.filter(s => s.status === options.status);
  }
  
  if (options.limit) {
    skills = skills.slice(0, options.limit);
  }
  
  if (options.json) {
    return { output: JSON.stringify(skills, null, 2) };
  }
  
  return { output: this.formatSkills(skills) };
}
```

**Example Output:**

```
Generated Skills (8 total)
══════════════════════════

✓ PUBLISHED: git-smart-workflow v1.0.0
  ClawHub:    https://clawhub.com/skills/git-smart-workflow
  Confidence: 94%
  Activations: 23
  Success Rate: 91%

✓ PUBLISHED: code-analyzer v1.0.0
  ClawHub:    https://clawhub.com/skills/code-analyzer
  Confidence: 87%
  Activations: 15
  Success Rate: 87%

○ PENDING: test-runner v0.1.0
  Location:   ~/.openclaw/skills/esass-generated/test-runner
  Confidence: 82%
  Awaiting:   Human approval

[Use 'esass:skills --status published' to filter]
```

---

### `esass:cycle`

Manually trigger a learning cycle.

```typescript
interface CycleCommand {
  name: 'esass:cycle';
  description: 'Trigger learning cycle manually';
  options: {
    dryRun?: boolean;    // Preview without saving
    force?: boolean;     // Skip min event threshold
    publish?: boolean;   // Publish generated skills
  };
}

async cmdCycle(options: CycleOptions): Promise<CommandResult> {
  if (this.loopController.isRunning() && !options.force) {
    return { 
      error: 'Learning cycle already running. Use --force to override.'
    };
  }
  
  const results = await this.loopController.runCycle({
    dryRun: options.dryRun,
    force: options.force,
    autoPublish: options.publish
  });
  
  return { output: this.formatCycleResults(results) };
}
```

**Example Output:**

```
Running Learning Cycle...
═════════════════════════

[1/5] Loading observations...
      ✓ Loaded 2,450 events from last 24 hours

[2/5] Detecting patterns...
      ✓ Found 5 new patterns (32 total)
      ✓ Identified 2 skill candidates

[3/5] Generating skills...
      ✓ Generated: test-runner (confidence: 0.82)

[4/5] Publishing skills...
      ⊘ Skipped: Auto-publish disabled

[5/5] Updating metrics...
      ✓ Cycle complete

Results:
  Duration:          12.4 seconds
  Events Processed:  2,450
  Patterns Detected: 5
  Skills Generated:  1
  Skills Published:  0

[Use --publish to auto-publish generated skills]
```

---

## Event Types Reference

### Emitted Events

The plugin emits events that other plugins can subscribe to:

```typescript
// Pattern detected
interface PatternDetectedEvent {
  type: 'esass:pattern:detected';
  pattern: PatternDefinition;
  isCandidate: boolean;
}

// Skill generated
interface SkillGeneratedEvent {
  type: 'esass:skill:generated';
  skill: SkillManifest;
  sourcePattern: PatternDefinition;
}

// Skill published
interface SkillPublishedEvent {
  type: 'esass:skill:published';
  skill: SkillManifest;
  clawHubUrl: string;
  version: string;
}

// Learning cycle complete
interface CycleCompleteEvent {
  type: 'esass:cycle:complete';
  results: CycleResults;
  duration: number;
}

// Skill evolution
interface SkillEvolvedEvent {
  type: 'esass:skill:evolved';
  oldSkills: SkillManifest[];
  newSkill: SkillManifest;
  evolutionType: 'merge' | 'absorb' | 'parameterize' | 'compose';
}
```

---

## Storage Layout

```
~/.openclaw/
├── plugins/
│   └── esass/
│       ├── config.yaml           # Plugin configuration
│       └── state.json            # Plugin state
│
├── esass/
│   ├── data/
│   │   ├── logs/                 # Observation logs
│   │   │   ├── log_20260201.jsonl
│   │   │   └── log_20260202.jsonl
│   │   │
│   │   ├── patterns/             # Detected patterns
│   │   │   └── pattern_*.json
│   │   │
│   │   └── metrics/              # Runtime metrics
│   │       └── metrics.json
│   │
│   └── cache/
│       ├── embeddings/           # Pattern embeddings
│       └── similarity/           # Similarity matrices
│
└── skills/
    └── esass-generated/          # Generated skills
        ├── git-smart-workflow/
        │   └── SKILL.md
        └── code-analyzer/
            └── SKILL.md
```

---

## Permissions

### Required Permissions

| Permission | Purpose | Scope |
|------------|---------|-------|
| `agent:observe` | Observe agent thinking and actions | Read-only |
| `tools:observe` | Observe tool executions | Read-only |
| `skills:write` | Generate and save skills | Write to skills dir |
| `storage:read` | Read observation data | Plugin data dir |
| `storage:write` | Write observation data | Plugin data dir |
| `network:clawhub` | Publish to ClawHub | External network |

### Permission Request

```typescript
// Plugin requests permissions on load
const permissions: PluginPermissions = {
  agent: ['observe'],
  tools: ['observe'],
  skills: ['write'],
  storage: ['read', 'write'],
  network: ['clawhub']
};

// User sees permission dialog:
// 
// ESASS Learning Engine requests:
// ✓ Observe agent thinking and actions
// ✓ Observe tool executions
// ✓ Generate and save skills
// ✓ Access plugin storage
// ✓ Connect to ClawHub (clawhub.com)
//
// [Allow] [Deny]
```

---

## Error Handling

### Error Types

```typescript
enum ESASSPluginError {
  // Observation errors
  OBSERVATION_FAILED = 'ESASS_OBSERVATION_FAILED',
  BUFFER_OVERFLOW = 'ESASS_BUFFER_OVERFLOW',
  STORAGE_WRITE_FAILED = 'ESASS_STORAGE_WRITE_FAILED',
  
  // Detection errors
  DETECTION_FAILED = 'ESASS_DETECTION_FAILED',
  INSUFFICIENT_DATA = 'ESASS_INSUFFICIENT_DATA',
  
  // Publishing errors
  SKILL_GENERATION_FAILED = 'ESASS_SKILL_GENERATION_FAILED',
  CLAWHUB_AUTH_FAILED = 'ESASS_CLAWHUB_AUTH_FAILED',
  CLAWHUB_PUBLISH_FAILED = 'ESASS_CLAWHUB_PUBLISH_FAILED',
  RATE_LIMIT_EXCEEDED = 'ESASS_RATE_LIMIT_EXCEEDED',
  
  // Loop errors
  CYCLE_FAILED = 'ESASS_CYCLE_FAILED',
  LOOP_ALREADY_RUNNING = 'ESASS_LOOP_ALREADY_RUNNING'
}
```

### Error Recovery

```typescript
// Graceful degradation on observation errors
async handleObservationError(error: Error, event: ObservationEvent): Promise<void> {
  this.context.logger.warn(`Observation failed: ${error.message}`);
  
  // Increment error counter
  this.metrics.observationErrors++;
  
  // If too many errors, pause observation
  if (this.metrics.observationErrors > 100) {
    this.context.logger.error('Too many observation errors, pausing...');
    await this.observer.pause();
    
    // Notify user
    this.context.notifications.warn(
      'ESASS observation paused due to errors. Check logs for details.'
    );
  }
}
```

---

## Installation

### Via OpenClaw CLI

```bash
# Install plugin
openclaw plugin install @esass/openclaw-plugin

# Enable plugin
openclaw plugin enable esass

# Configure
openclaw plugin config esass --set loop.autoStart=true

# Verify
openclaw plugin status esass
```

### Via Configuration

```yaml
# ~/.openclaw/config.yaml
plugins:
  esass:
    enabled: true
    config:
      observation:
        enabled: true
      loop:
        autoStart: true
      publishing:
        autoPublish: false
```

---

## Changelog

### v1.0.0 (2026-02-01)

- Initial release
- Full observation pipeline with tool, reasoning, and decision probes
- Pattern detection with PrefixSpan algorithm
- Skill generation with SKILL.md formatting
- ClawHub integration for publishing
- Learning loop controller with configurable timing
- Plugin commands for status, patterns, skills, and manual cycles
- Comprehensive configuration schema
- Permission-based security model

---

*This plugin specification defines the integration between ESASS and OpenClaw, enabling a recursive skill learning loop where AI agents continuously improve through observation and pattern crystallization.*
