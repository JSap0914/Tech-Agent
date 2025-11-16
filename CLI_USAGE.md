# Tech Spec Agent - CLI Usage Guide

## Overview

The Tech Spec Agent CLI provides a terminal-based interface for generating Technical Requirements Documents (TRD) from PRD and design documents. This eliminates the need for a web frontend and allows the agent to run entirely in your local environment.

## Installation

Dependencies are already installed. If you need to reinstall:

```bash
./venv/Scripts/pip.exe install click rich prompt-toolkit
```

## Quick Start

### 1. Prepare Your Input Documents

Create a folder structure like this:

```
project/
├── inputs/
│   ├── prd.md                      # Product Requirements Document
│   └── design-docs/
│       ├── design_system.md        # Design system (required)
│       ├── ux_flow.md              # UX flow (required)
│       ├── screen_specs.md         # Screen specs (required)
│       ├── wireframes.md           # Wireframes (optional)
│       └── component_library.md    # Component library (optional)
└── outputs/                        # Auto-created for generated docs
```

Sample test files are available in `test-inputs/` folder.

### 2. Run the Workflow

```bash
python -m cli.main start \
  --prd ./test-inputs/prd.md \
  --design-docs ./test-inputs/design-docs \
  --output ./outputs
```

### 3. Interactive Workflow

The agent will:
1. **Analyze PRD completeness** - Display score and missing/ambiguous elements
2. **Identify technology gaps** - Find undecided technical choices
3. **Research technologies** - Present 3 options for each gap with pros/cons/metrics
4. **Wait for your decision** - You select: `1`, `2`, `3`, or `ai` for recommendation
5. **Parse code (if provided)** - Infer API specs from Google AI Studio code
6. **Generate documents** - Create TRD, API spec, DB schema, architecture, tech stack
7. **Save to filesystem** - All documents saved to output directory

## Commands

### `start` - Start New Workflow

Generate Tech Spec documents from PRD and design documents.

```bash
python -m cli.main start \
  --prd <path-to-prd.md> \
  --design-docs <path-to-design-docs-folder> \
  [--ai-studio <path-to-zip>] \
  [--output ./outputs] \
  [--project-id <uuid>] \
  [--user-id <uuid>]
```

**Options:**
- `--prd`: Path to PRD markdown file (required)
- `--design-docs`: Path to folder containing design documents (required)
- `--ai-studio`: Path to Google AI Studio code ZIP (optional)
- `--output`: Output directory for generated documents (default: `./outputs`)
- `--project-id`: Project UUID (optional, auto-generated if not provided)
- `--user-id`: User UUID (optional, auto-generated if not provided)

**Example:**
```bash
python -m cli.main start \
  --prd ./test-inputs/prd.md \
  --design-docs ./test-inputs/design-docs \
  --output ./my-project-trd
```

### `example` - Show Example Structure

Display the expected folder structure for inputs.

```bash
python -m cli.main example
```

### `health` - System Health Check

Check API keys and database connection status.

```bash
# Check API keys
python -m cli.main health --check-apis

# Check database connection
python -m cli.main health --check-db

# Check both
python -m cli.main health --check-apis --check-db
```

### `resume` - Resume Paused Workflow

**Note:** Not yet implemented in CLI mode. Requires database checkpointing.

```bash
python -m cli.main resume --session-id <uuid>
```

### `list-sessions` - List All Sessions

**Note:** Not yet implemented in CLI mode. Requires database connection.

```bash
python -m cli.main list-sessions
```

## User Interaction During Workflow

### Technology Selection

When the agent presents technology options:

```
======================================================================
Technology Research: AUTHENTICATION (1/3)
======================================================================

Select Technology for authentication

┏━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ # ┃ Technology   ┃ Metrics      ┃ Pros        ┃ Cons        ┃
┡━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 1 │ [*] NextAuth │ Stars: 15k   │ + Easy to   │ - Limited   │
│   │              │ Downloads:   │   integrate │   custom    │
│   │              │ 500k/wk      │ + Good docs │             │
│ 2 │ Auth0        │ Stars: 8k    │ + Enterprise│ - Pricing   │
│   │              │ SaaS         │   features  │   concerns  │
│ 3 │ Passport.js  │ Stars: 20k   │ + Flexible  │ - More      │
│   │              │ Downloads:   │ + Popular   │   setup     │
│   │              │ 1M/wk        │             │             │
└───┴──────────────┴──────────────┴─────────────┴─────────────┘

Your choice (1/2/3/ai/search): _
```

**Input options:**
- `1`, `2`, `3` - Select specific technology
- `ai` - Accept AI recommendation (marked with `[*]`)
- `search` - Search for custom technology (not yet implemented)

### Clarification Questions

If PRD completeness score < 80, you'll be asked clarification questions:

```
[INFO] Please answer 3 clarification questions:

Question 1/3:
  What authentication method should be used? (OAuth, JWT, session-based)

Your answer: _
```

## Generated Documents

After successful completion, you'll find these files in the output directory:

```
outputs/
├── trd_20250116_143022.md                    # Main Technical Requirements Document
├── api_spec_20250116_143022.yaml             # OpenAPI specification
├── db_schema_20250116_143022.sql             # Database schema (DDL + ERD)
├── architecture_20250116_143022.mmd          # Mermaid architecture diagrams
├── tech_stack_20250116_143022.md             # Technology stack documentation
└── session_metadata_20250116_143022.json     # Session metadata & decisions
```

## Environment Variables

Ensure these are set in your `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
TAVILY_API_KEY=tvly-dev-...
DATABASE_URL=postgresql+asyncpg://...     # Optional for CLI
REDIS_URL=redis://...                     # Optional for CLI
```

The CLI will use the `.env` file in the Tech Agent directory.

## Progress Tracking

The CLI displays real-time progress through 4 phases:

- **Phase 1 (0-25%)**: Input & Analysis
  - Load inputs
  - Analyze PRD completeness
  - Ask clarification questions
  - Identify technology gaps

- **Phase 2 (25-50%)**: Technology Research & Selection
  - Research open-source technologies
  - Present options
  - Wait for user decisions
  - Validate selections
  - Loop until all gaps resolved

- **Phase 3 (50-65%)**: Code Analysis
  - Parse Google AI Studio code (if provided)
  - Infer API specifications from React components

- **Phase 4 (65-100%)**: Document Generation
  - Generate TRD (with quality validation, retry up to 3x)
  - Generate API specification (OpenAPI YAML)
  - Generate database schema (SQL DDL)
  - Generate architecture diagrams (Mermaid)
  - Generate tech stack documentation
  - Save all documents to filesystem

## Keyboard Shortcuts

- **Ctrl+C** - Cancel workflow (graceful exit with checkpoint save)
- **Enter** - Confirm default selections

## Troubleshooting

### Unicode/Emoji Errors

The CLI has been updated to use ASCII-compatible characters for Windows compatibility. If you still see encoding errors, ensure your terminal uses UTF-8 encoding.

### API Key Not Found

```
[ERROR] ANTHROPIC_API_KEY: Not set
```

**Solution:** Ensure `.env` file exists in Tech Agent directory with valid API keys.

### Module Not Found Error

```
ModuleNotFoundError: No module named 'cli'
```

**Solution:** Always run the CLI using `python -m cli.main` from the Tech Agent directory, not `python cli/main.py`.

### Missing Design Documents

```
[ERROR] Required design document missing: design_system.md
```

**Solution:** Ensure all required design documents exist:
- `design_system.md`
- `ux_flow.md`
- `screen_specs.md`

Optional documents (`wireframes.md`, `component_library.md`) are not required.

## Differences from Web Interface

| Feature | Web Interface | CLI |
|---------|---------------|-----|
| **Input** | API endpoints + database | Local files |
| **Progress** | WebSocket updates | Terminal output |
| **User decisions** | UI buttons | Terminal prompts |
| **State persistence** | PostgreSQL checkpointer | Optional (not yet implemented) |
| **Resume capability** | Yes (from database) | Not yet implemented |
| **Output** | Database + S3 | Local filesystem |

## Next Steps

To actually run the workflow with real AI processing:

1. Ensure `.env` has valid `ANTHROPIC_API_KEY` and `TAVILY_API_KEY`
2. Prepare your PRD and design documents
3. Run: `python -m cli.main start --prd <path> --design-docs <path>`
4. Respond to technology selection prompts
5. Wait for document generation (15-25 minutes typical)
6. Review generated documents in output directory

## Future Enhancements

- **Resume capability**: Resume paused workflows from JSON checkpoints
- **Session management**: List and manage CLI sessions
- **Custom search**: Search for technologies not in top 3 recommendations
- **Batch mode**: Non-interactive mode with pre-selected technologies
- **Export formats**: PDF, Word document generation
