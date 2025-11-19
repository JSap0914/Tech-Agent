# Tech Spec Agent - Terminal CLI Usage Guide

**The terminal CLI already exists and is ready to use!**
This guide shows you how to run the agent in your terminal with a beautiful, interactive interface.

---

## Quick Start

### 1. Prepare Your Input Files

Create an `inputs/` directory with:

```
inputs/
├── prd.md                      # Your Product Requirements Document
├── design-docs/
│   ├── design_system.md        # Design system
│   ├── ux_flow.md              # UX flow
│   ├── screen_specs.md         # Screen specifications
│   ├── wireframes.md           # Wireframes (optional)
│   └── component_library.md    # Component library (optional)
└── ai_studio_code.zip          # Google AI Studio code (optional)
```

### 2. Run the CLI

```bash
# Navigate to project
cd "C:\Users\Han\Documents\SKKU 1st Grade\Tech Agent"

# Activate virtual environment
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Run the agent
python -m cli.main start \
  --prd ./inputs/prd.md \
  --design-docs ./inputs/design-docs \
  --output ./outputs
```

### 3. Watch the Magic Happen!

The terminal will show:
- ✅ Real-time progress bars (0-100%)
- ✅ Phase indicators (Analysis → Research → Code → Generation)
- ✅ Beautiful formatted tables for technology options
- ✅ Interactive prompts for your decisions
- ✅ Live document generation status
- ✅ Final output summary with file paths

---

## What You'll See

### Phase 1: Input & Analysis (0-25%)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tech Spec Agent CLI v1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ Loading input documents...
✓ All input documents loaded successfully

Phase 1: Input & Analysis | load_inputs | [#####---------------] 10.0%
  Loading PRD and design documents from database...

Phase 1: Input & Analysis | analyze_completeness | [##########-----------] 20.0%
  Analyzing PRD completeness...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRD Completeness Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Completeness Score: 75/100

Missing Elements:
  • API authentication method not specified
  • Database scaling strategy unclear
  • File storage solution not mentioned

Ambiguous Elements:
  • "Real-time features" - unclear scope
  • "Mobile support" - native apps or responsive web?
```

**If score < 80**, you'll be asked clarification questions:
```
Question 1/3:
What API authentication method should be used?

Your answer: JWT with refresh tokens
```

---

### Phase 2: Technology Research & Selection (25-50%)

```
Phase 2: Technology Research | research_technologies | [#################-----] 35.0%
  Researching open-source technologies (5 categories)...
  ✓ authentication - 3 options found
  ✓ database - 3 options found
  ✓ file_upload - 3 options found
  ✓ email - 3 options found
  ✓ payments - 3 options found
```

Then, for each technology gap, you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Technology Decision 1/5: AUTHENTICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User authentication and session management needed

┏━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ # ┃ Technology   ┃ Metrics      ┃ Pros        ┃ Cons        ┃
┡━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 1 │ ⭐ NextAuth  │ ★ 15,234     │ + Easy      │ - Limited   │
│   │              │ ↓ 485k/wk    │   setup     │   custom    │
│   │              │ 📚 Excellent │ + Good docs │             │
├───┼──────────────┼──────────────┼─────────────┼─────────────┤
│ 2 │ Auth0        │ ★ 8,123      │ + Enterprise│ - Pricing   │
│   │              │ SaaS         │   features  │   concerns  │
│   │              │ 📚 Good      │ + Compliant │             │
├───┼──────────────┼──────────────┼─────────────┼─────────────┤
│ 3 │ Passport.js  │ ★ 22,456     │ + Flexible  │ - More      │
│   │              │ ↓ 1.2M/wk    │ + 500+ auth │   setup     │
│   │              │ 📚 Good      │   strategies│             │
└───┴──────────────┴──────────────┴─────────────┴─────────────┘

Your choice (1/2/3/ai/search): _
```

**Your Options:**
- Type `1`, `2`, or `3` to select an option
- Type `ai` to accept AI recommendation (⭐ marked)
- Type `search` to enter a custom technology name

**Example:**
```
Your choice: 1
Why did you choose NextAuth.js? (optional): Best for Next.js apps

✅ NextAuth.js selected for authentication
```

---

### Phase 3: Code Analysis (50-65%)

```
Phase 3: Code Analysis | parse_ai_studio_code | [########################------] 60.0%
  Parsing Google AI Studio generated code...
  ✓ Extracted 12 React components
  ✓ Found 18 API call patterns

Phase 3: Code Analysis | infer_api_spec | [###########################---] 65.0%
  Inferred 18 API endpoints from code:
  • GET /api/users/profile
  • POST /api/users/register
  • PATCH /api/users/settings
  • GET /api/projects
  • POST /api/projects
  ...
```

---

### Phase 4: Document Generation (65-100%)

```
Phase 4: Document Generation | generate_trd | [##################################] 70.0%
  Generating Technical Requirements Document...
  ✓ Project overview section
  ✓ Technology stack section (includes your selections)
  ✓ API specifications section
  ✓ Database design section
  ✓ Security considerations section

Phase 4: Document Generation | validate_trd | [#####################################] 75.0%
  TRD Quality Score: 92/100
  ✓ Completeness: 95/100
  ✓ Technical Accuracy: 90/100
  ✓ Requirements Coverage: 91/100

Phase 4: Document Generation | generate_api_spec | [########################################] 80.0%
  Generated OpenAPI 3.0 specification:
  • 18 endpoints documented
  • Authentication: Bearer JWT
  • Rate limiting: 100 req/min

Phase 4: Document Generation | generate_db_schema | [###########################################] 85.0%
  Generated database schema:
  • 8 tables created
  • 15 relationships defined
  • 12 indexes for performance

Phase 4: Document Generation | generate_architecture | [################################################] 90.0%
  Generated architecture diagrams:
  • System overview diagram
  • Component interaction diagram
  • Deployment architecture
  • Data flow diagram

Phase 4: Document Generation | generate_tech_stack_doc | [###################################################] 95.0%
  Generated technology stack documentation:

  FRONTEND:
  • Next.js 14 - React framework with SSR
  • TailwindCSS - Utility-first CSS
  • NextAuth.js - Authentication

  BACKEND:
  • Node.js + Express - API server
  • PostgreSQL - Primary database
  • Redis - Caching layer

  INFRASTRUCTURE:
  • AWS S3 - File storage
  • Vercel - Frontend hosting
  • Railway - Backend hosting

Phase 4: Document Generation | save_to_db | [######################################################] 98.0%
  Saving documents to filesystem...

Phase 4: Document Generation | notify_next_agent | [#########################################################] 100.0%
```

---

### Final Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Tech Spec Generation Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated Documents:
  ✓ Technical Requirements Document (TRD)
      outputs/trd_20250116_143022.md

  ✓ API Specification (OpenAPI YAML)
      outputs/api_spec_20250116_143022.yaml

  ✓ Database Schema (SQL DDL + ERD)
      outputs/db_schema_20250116_143022.sql
      outputs/db_erd_20250116_143022.mmd

  ✓ Architecture Diagrams (Mermaid)
      outputs/architecture_20250116_143022.mmd

  ✓ Technology Stack Documentation
      outputs/tech_stack_20250116_143022.md

  ✓ Session Metadata
      outputs/session_metadata_20250116_143022.json

Quality Score: 92/100

Total Time: 18 minutes 34 seconds

All documents saved to: ./outputs/

Next Step: Review documents and proceed to Backlog Agent
```

---

## CLI Commands

### Start Workflow
```bash
python -m cli.main start \
  --prd <path-to-prd.md> \
  --design-docs <path-to-design-folder> \
  --output <output-directory> \
  [--ai-studio <path-to-zip>] \
  [--project-id <uuid>] \
  [--user-id <uuid>]
```

### Health Check
```bash
# Check API keys
python -m cli.main health --check-apis

# Check database connection
python -m cli.main health --check-db

# Check everything
python -m cli.main health --check-apis --check-db
```

**Example Output:**
```
Running health checks...

✓ ANTHROPIC_API_KEY: Set (length: 108)
✓ TAVILY_API_KEY: Set (length: 48)
✓ Database: Connected

All health checks passed!
```

### Show Example Structure
```bash
python -m cli.main example
```

Shows expected folder structure for inputs.

### Version
```bash
python -m cli.main --version
```

---

## Configuration

The CLI uses the same `.env` file as the web API.

**Required Environment Variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

**Optional Environment Variables:**
```bash
# Database (for checkpointing and resume)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0

# LLM settings
ANTHROPIC_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_TEMPERATURE=0.7
ANTHROPIC_MAX_TOKENS=4096

# Research settings
TAVILY_MAX_RESULTS=10
TAVILY_SEARCH_DEPTH=basic
```

---

## Advanced Usage

### Custom Project/User IDs
```bash
python -m cli.main start \
  --prd ./inputs/prd.md \
  --design-docs ./inputs/design-docs \
  --project-id "my-project-123" \
  --user-id "user-456"
```

### Different Output Directory
```bash
python -m cli.main start \
  --prd ./inputs/prd.md \
  --design-docs ./inputs/design-docs \
  --output ./my-custom-outputs
```

### With Google AI Studio Code
```bash
python -m cli.main start \
  --prd ./inputs/prd.md \
  --design-docs ./inputs/design-docs \
  --ai-studio ./inputs/ai_studio_code.zip
```

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"
**Solution:** Set API key in `.env` file or environment
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Error: "PRD file not found"
**Solution:** Check file path is correct
```bash
ls -la ./inputs/prd.md  # Verify file exists
```

### Error: "Design docs folder empty"
**Solution:** Ensure at least one `.md` file exists in design-docs folder
```bash
ls -la ./inputs/design-docs/
```

### Workflow hangs at decision prompt
**Solution:** Type your choice and press Enter
- Valid inputs: `1`, `2`, `3`, `ai`, `search`

### Ctrl+C to cancel
Press `Ctrl+C` to cancel the workflow at any time.
```
ℹ Workflow cancelled by user.
```

---

## Comparison: CLI vs Web Interface

| Feature | CLI | Web Interface |
|---------|-----|---------------|
| **Progress Updates** | Terminal progress bars | WebSocket streaming |
| **Technology Options** | Rich tables | UI cards with images |
| **User Decisions** | Text input (1/2/3/ai) | Button clicks |
| **Clarifications** | Terminal prompts | Form inputs |
| **Document Preview** | File paths only | Inline markdown |
| **State Persistence** | Optional (JSON/DB) | PostgreSQL |
| **Resume Capability** | Future enhancement | Yes |
| **Authentication** | Not required | JWT required |
| **Output** | Local filesystem | Database + S3 |
| **Deployment** | Local Python script | FastAPI server |

---

## Next Steps

1. **Try the CLI**: Run the quick start example above
2. **Review outputs**: Check generated documents in `outputs/` directory
3. **Customize**: Modify output directory, add AI Studio code
4. **Integrate**: Use generated TRD for backlog agent

---

## Tips & Best Practices

### 1. Organize Your Inputs
Keep a consistent structure:
```
my-project/
├── inputs/
│   ├── prd.md
│   └── design-docs/
│       ├── design_system.md
│       ├── ux_flow.md
│       └── screen_specs.md
└── outputs/  # Auto-generated
```

### 2. Use AI Recommendations
The `ai` option selects the ⭐ recommended technology based on:
- Your project requirements
- Technology popularity and maturity
- Integration complexity
- Community support

### 3. Provide Context in Reasoning
When selecting technologies, brief reasoning helps:
```
Your choice: 1
Why? Best for Next.js, good OAuth support, rapid development
```

### 4. Save Session Metadata
The `session_metadata.json` file contains:
- All technology decisions
- Quality scores
- Completeness analysis
- Timing information

Use it for future reference!

### 5. Review Before Production
The CLI generates v1 documents. Always review:
- TRD completeness
- API spec accuracy
- Database schema indexes
- Architecture scalability

---

## Future Enhancements (Planned)

- [ ] **Demo Mode**: Simulated workflow without API calls
- [ ] **Interactive Tutorial**: Step-by-step learning mode
- [ ] **Resume Sessions**: Restore from JSON checkpoints
- [ ] **Document Preview**: Show TRD snippets in terminal
- [ ] **Visual ASCII Diagrams**: Render architecture in terminal
- [ ] **Session Management**: List/delete previous sessions

---

**Ready to generate your first TRD? Run:**

```bash
python -m cli.main start \
  --prd ./inputs/prd.md \
  --design-docs ./inputs/design-docs \
  --output ./outputs
```

🚀 **Happy tech spec generation!**
