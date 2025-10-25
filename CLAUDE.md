# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AutoVideoEditor** project using the **SpecKit** framework for specification-driven development. The repository is currently empty (no application code yet) and contains only the SpecKit workflow infrastructure.

SpecKit enables structured feature development through specification → planning → implementation phases.

## Development Workflow

### Feature Development Lifecycle

Features are developed through slash commands that guide you through each phase:

1. **Specify** (`/speckit.specify <feature description>`)
   - Creates feature branch and specification
   - Generates `specs/###-feature-name/spec.md`
   - Validates requirements and success criteria
   - Creates quality checklist

2. **Clarify** (`/speckit.clarify`)
   - Identifies underspecified areas
   - Asks up to 5 targeted questions
   - Updates spec with answers

3. **Plan** (`/speckit.plan`)
   - Creates implementation plan (`plan.md`)
   - Generates data models, API contracts
   - Produces `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

4. **Tasks** (`/speckit.tasks`)
   - Generates actionable task breakdown (`tasks.md`)
   - Organizes by user story priority
   - Identifies parallel execution opportunities

5. **Implement** (`/speckit.implement`)
   - Executes tasks from `tasks.md`
   - Follows TDD approach if tests specified
   - Validates checklists before proceeding

### Supporting Commands

- `/speckit.constitution` - Create/update project principles
- `/speckit.checklist` - Generate custom validation checklists
- `/speckit.analyze` - Cross-artifact consistency analysis

## Repository Structure

```
.claude/commands/          # Slash command definitions
.specify/
  ├── memory/              # Project constitution
  ├── scripts/powershell/  # Workflow automation scripts
  └── templates/           # Spec, plan, and task templates
specs/                     # Created by /speckit.specify
  └── ###-feature-name/    # Each feature gets numbered directory
      ├── spec.md          # Feature specification
      ├── plan.md          # Implementation plan
      ├── tasks.md         # Task breakdown
      ├── checklists/      # Quality validation
      ├── contracts/       # API specifications
      ├── data-model.md    # Entity definitions
      ├── research.md      # Technical decisions
      └── quickstart.md    # Integration scenarios
```

## Key Scripts

All scripts are PowerShell-based and support JSON output via `-Json` flag:

- **check-prerequisites.ps1** - Validates workflow prerequisites
  - `-RequireTasks` - Ensures tasks.md exists
  - `-IncludeTasks` - Includes tasks.md in output
  - `-PathsOnly` - Returns paths only (no validation)

- **create-new-feature.ps1** - Initializes feature branch and structure
  - Automatically determines next feature number
  - Creates branch: `###-short-name`
  - Initializes spec directory

- **setup-plan.ps1** - Prepares planning phase
  - Validates spec exists
  - Copies plan template

- **update-agent-context.ps1** - Updates AI agent context
  - `-AgentType claude` - Updates Claude-specific context

## Specification Requirements

### Mandatory Spec Sections
- User Scenarios & Testing (prioritized as P1, P2, P3...)
- Functional Requirements (FR-001, FR-002...)
- Success Criteria (measurable, technology-agnostic)

### Quality Standards
- No implementation details in specifications
- Requirements must be testable and unambiguous
- Success criteria must be measurable without tech specifics
- Maximum 3 [NEEDS CLARIFICATION] markers
- User stories must be independently testable

### Task Format Requirements

Every task in `tasks.md` must follow this strict format:
```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

Components:
- Checkbox: `- [ ]`
- Task ID: T001, T002, T003... (sequential)
- [P]: Optional parallel execution marker
- [Story]: [US1], [US2], [US3]... for user story tasks only
- Description: Action verb + exact file path

## Implementation Notes

### Branch Naming
- Format: `###-short-name` (e.g., `001-user-auth`)
- Number is auto-incremented across:
  - Remote branches
  - Local branches
  - Specs directories

### Test-Driven Development
- Tests are OPTIONAL (only if explicitly requested)
- When tests exist, they execute before implementation
- Contract tests run before endpoint implementation

### Task Execution Order
1. **Phase 1**: Setup (project initialization)
2. **Phase 2**: Foundational (blocking prerequisites)
3. **Phase 3+**: User Stories (by priority P1, P2, P3...)
4. **Final Phase**: Polish & cross-cutting concerns

### Parallel Execution
- Tasks marked [P] can run concurrently
- Tasks affecting same files must run sequentially
- Phase completion required before next phase

## Git Configuration Note

This repository is on a network share and may require git safe.directory configuration:
```bash
git config --global --add safe.directory '%(prefix)///SyNas1/Shared/tools/AutoVideoEditor/AutoVideoEditor'
```

## Constitution

Project principles are defined in `.specify/memory/constitution.md`. All features must comply with constitutional requirements. Use `/speckit.constitution` to create or update project-wide development principles.
