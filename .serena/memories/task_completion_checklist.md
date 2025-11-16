# Task Completion Checklist

When completing a task, follow this checklist to ensure code quality and project standards.

## Before Writing Code

1. **Read Documentation**: Check CLAUDE.md, README.md, and relevant WEEK_*_COMPLETE.md files
2. **Understand Context**: Review state schema (src/langgraph/state.py) if working with LangGraph nodes
3. **Check Existing Patterns**: Read similar code to match the established style
4. **Verify Dependencies**: Ensure required packages are in pyproject.toml

## While Writing Code

1. **Follow Code Style**:
   - Line length: 100 characters
   - Type hints: Required for all functions
   - Docstrings: Google style for all public functions
   - Logging: Use structlog with structured format
   
2. **LangGraph Node Pattern**:
   ```python
   async def node_name_node(state: TechSpecState) -> TechSpecState:
       """Brief description.
       
       Args:
           state: Current workflow state
       
       Returns:
           Updated state with modifications
       """
       logger.info("action_start", session_id=state["session_id"])
       
       try:
           # Implementation
           state["field"] = value
           state["conversation_history"].append({...})
           logger.info("action_complete", ...)
       except Exception as e:
           logger.error("action_error", ..., exc_info=True)
           state["errors"].append({...})
           raise
       
       return state
   ```

3. **Error Handling**:
   - Use try-except blocks
   - Log errors with structlog
   - Append to state["errors"] if applicable
   - Distinguish recoverable vs non-recoverable

4. **State Management**:
   - Only modify state fields defined in state.py
   - Use correct field names (e.g., "inferred_apis" not "inferred_api_spec")
   - For append-only fields, use: `state["field"].append(...)` not `state["field"] = [...]`

## After Writing Code

### 1. Code Formatting
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Verify
black --check src/ tests/
isort --check src/ tests/
```

### 2. Linting
```bash
# Lint and auto-fix
ruff check src/ tests/ --fix

# Verify no remaining issues
ruff check src/ tests/
```

### 3. Type Checking
```bash
# Type check source code
mypy src/

# Fix any type errors reported
```

### 4. Testing

#### Write Tests
- **Unit Tests**: For individual functions/classes (tests/unit/)
- **Integration Tests**: For workflows and API endpoints (tests/integration/)
- **Coverage Target**: 80%+

#### Run Tests
```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing -v

# Verify coverage >= 80%
# Check htmlcov/index.html for details
```

### 5. Documentation

#### Update Documentation
- **Code Comments**: For complex logic
- **Docstrings**: For all public functions
- **WEEK_*_COMPLETE.md**: If completing a weekly milestone
- **README.md**: If adding new features or changing setup

#### Create Completion Document (for weekly milestones)
Create a `WEEK_X_COMPLETE.md` file with:
- Overview of changes
- Files modified with line numbers
- New functions/features added
- Testing recommendations
- Impact assessment
- Known limitations

### 6. Database Changes

If schema changes are needed:
```bash
# Create migration
alembic revision --autogenerate -m "description_of_change"

# Review generated migration file
# Edit alembic/versions/<timestamp>_description.py if needed

# Apply migration
alembic upgrade head

# Verify database state
psql -U postgres -d anyon_db -c "\dt"
```

### 7. Environment Variables

If new config needed:
1. Add to `.env.example` with description and example value
2. Add to `src/config.py` with pydantic-settings
3. Document in README.md Configuration section

### 8. Git Workflow

```bash
# Check status
git status

# Stage changes
git add <files>

# Commit with descriptive message
git commit -m "Clear description of what and why"

# Example commit messages:
# - "Add GraphQL support to API inference (Week 9)"
# - "Fix state schema mismatch in infer_api_spec_node"
# - "Improve TRD generation with few-shot examples (Week 8)"

# Push to remote
git push origin branch-name
```

### 9. Final Verification

Before marking task complete:
- [ ] Code formatted (black, isort)
- [ ] No linting errors (ruff)
- [ ] No type errors (mypy)
- [ ] Tests written and passing
- [ ] Coverage >= 80%
- [ ] Documentation updated
- [ ] Database migrations applied (if needed)
- [ ] Environment variables documented (if needed)
- [ ] Git committed with clear message
- [ ] Manual testing completed (if applicable)

## Weekly Milestone Completion

For completing weekly tasks:
1. Complete all items in checklist above
2. Create `WEEK_X_COMPLETE.md` with comprehensive documentation
3. Update `WEEK_X_FIXES.md` if fixing issues found in review
4. Verify all claimed features actually work (don't just define, but wire into workflow)
5. Test integration with upstream/downstream nodes
6. Check state field compatibility across all nodes

## Common Pitfalls to Avoid

1. **❌ Defining but not using**: Don't create functions that are never called
2. **❌ State field mismatches**: Always check state.py for correct field names
3. **❌ Overwrit instead of append**: Use `.append()` for conversation_history, errors, etc.
4. **❌ Missing type hints**: All functions need type annotations
5. **❌ No docstrings**: All public functions need documentation
6. **❌ Ignoring tests**: Write tests for new code
7. **❌ Hardcoding values**: Use config.py and environment variables
8. **❌ Not logging errors**: Always log with structlog
9. **❌ Breaking existing code**: Check integration with other nodes
10. **❌ Claiming features work without verification**: Test the complete data flow
