# Folder Creation Guide for Task Organization

## Overview
This guide defines the standard folder structure used in this workspace for organizing task-specific automation, debugging, and integration work. Use this template when asking Codex to create a new task folder.

## Folder Structure Template

When creating a new task folder (e.g., `[TASKNAME]/`), Codex should create the following files:

```
[TASKNAME]/
├── AGENTS.md                          # Operating principles & rules
├── [TASKNAME]_INTEGRATION_ENABLEMENT.md  # Mission/objective definition
├── [TASKNAME]_WORKING_RUNBOOK.md      # Step-by-step practical procedures
├── [TASKNAME]_REMEDIATION_LOG.md      # Log of changes & actions taken
└── current_task/                      # Subdirectory for task-specific files
    └── [TASKNAME]_REMEDIATION_LOG.md  # Active task-specific log
```

## File Descriptions

### 1. AGENTS.md
**Purpose**: High-level operating procedures and rules for operators.

**Should include**:
- Repo/workspace purpose statement
- Task file rules (when to defer to mission-specific markdown)
- Core operating principles (e.g., "Act like an operator, not a note-taker")
- Access requirements (SSH keys, credentials, discovery commands)
- When to update logs and remediation tracking
- Any workspace-specific context or prequisites

**Length**: 1-2 pages typically

### 2. [TASKNAME]_INTEGRATION_ENABLEMENT.md
**Purpose**: Define the mission, objective, and acceptance criteria.

**Should include**:
- Clear objective statement
- Primary target(s) or system(s) being integrated
- Specific capabilities/workflows that need to work
- What constitutes "complete" (not just identifying blockers)
- Key preconditions or dependencies
- Any context about upstream repos, services, or environments

**Length**: 1-2 pages typically

### 3. [TASKNAME]_WORKING_RUNBOOK.md
**Purpose**: Practical sequence of steps that worked for this specific task.

**Should include**:
- Clear purpose statement (what this runbook achieves)
- Scope (target paths, environments, workflows)
- Preconditions/prerequisites
- Expected steady-state outcome
- Numbered step-by-step procedures
- Troubleshooting or gotchas discovered

**Length**: 3-5+ pages depending on complexity

### 4. [TASKNAME]_REMEDIATION_LOG.md
**Purpose**: Running log of all changes, fixes, and actions taken during task execution.

**Should include**:
- Timestamp or session markers
- Command run
- File changed
- Issue discovered and fix applied
- Output or results
- Updated after every meaningful action (not just at the end)

**Format**: Chronological entries making it easy to replay or understand what happened

### 5. current_task/[TASKNAME]_REMEDIATION_LOG.md
**Purpose**: Active, task-specific remediation log for the current work being done.

**Should include**:
- Same structure as the parent remediation log
- Reference back to parent AGENTS.md for "treat as mission-specific source of truth"
- Kept updated throughout active task execution

---

## Instruction for Codex

When you want Codex to create a new folder, provide:

1. **Folder name** (e.g., "myservice-integration")
2. **Clear objective** of what the folder is for
3. **Key context** (target systems, environments, access requirements)
4. **Expected outcomes** (what success looks like)

### Example Request to Codex:
```
Create a new task folder called "redis-cluster-setup" using the folder creation template.

Objective: Set up and validate Redis cluster on ECS GPU instances.

Context:
- Target environment: ECS GPU containers
- Access: SSH via existing key
- Primary workflows: cluster initialization, failover testing, performance validation

Include all 5 standard files (AGENTS.md, INTEGRATION_ENABLEMENT, WORKING_RUNBOOK, REMEDIATION_LOGs, current_task/ subdirectory).
```

---

## Key Principles for These Folders

1. **AGENTS.md is the operating charter** - defines how work gets done in this context
2. **_INTEGRATION_ENABLEMENT sets the mission** - what needs to be true when done
3. **_WORKING_RUNBOOK is practical** - the steps that actually worked, not generic docs
4. **_REMEDIATION_LOG is a record** - updated continuously, not at the end
5. **current_task/ keeps active logs scoped** - separate working log from final documentation

---

## File Naming Convention

Replace `[TASKNAME]` with the folder name in lowercase with underscores, e.g.:
- Folder: `video2robot` → Files: `VIDEO2ROBOT_*.md`
- Folder: `redis-cluster` → Files: `REDIS_CLUSTER_*.md`
- Folder: `auth-integration` → Files: `AUTH_INTEGRATION_*.md`
