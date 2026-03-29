# AI Agent Team Conventions

## Core Principles

1. ai_run.py is reusable engine code
2. Project-specific intelligence lives in:
   - .ai/project_config.json
   - .ai/CLAUDE.md
   - .ai/skills/
3. Agents are generic role definitions
4. Skills are domain- and stack-specific
5. Files inside .ai/runs/<TICKET>/ are the source of truth for each workflow run

## Workflow Model

prepare -> human executes prompt in Claude/Copilot -> complete

## Prompt Strategy

Prompts should:

- reference files directly
- instruct the agent to write outputs to target files
- avoid giant pasted context when file access is available

## Reuse Strategy

Reuse:

- ai_run.py
- agents/
- templates/

Customize per project:

- project_config.json
- CLAUDE.md
- skills/
