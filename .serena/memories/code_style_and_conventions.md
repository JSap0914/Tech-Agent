# Code Style and Conventions

## Python Version
- **Target**: Python 3.11+
- **Current**: Python 3.13.7

## Code Formatting

### Black
- **Line Length**: 100 characters
- **Target Version**: py311
- **Include Pattern**: `\.pyi?$`
- **Exclude**: .eggs, .git, .hg, .mypy_cache, .tox, .venv, build, dist

### isort
- **Profile**: black (compatible with Black)
- **Line Length**: 100
- **Multi-line Output**: 3
- **Include Trailing Comma**: true
- **Force Grid Wrap**: 0
- **Use Parentheses**: true
- **Ensure Newline Before Comments**: true

## Linting (Ruff)
- **Line Length**: 100
- **Target Version**: py311
- **Selected Rules**:
  - E: pycodestyle errors
  - W: pycodestyle warnings
  - F: pyflakes
  - I: isort
  - B: flake8-bugbear
  - C4: flake8-comprehensions
  - UP: pyupgrade
- **Ignored**:
  - E501: line too long (handled by black)
  - B008: function calls in argument defaults
  - C901: too complex
- **Special**: F401 ignored in `__init__.py` files

## Type Checking (mypy)
- **Python Version**: 3.11
- **Warn Return Any**: true
- **Warn Unused Configs**: true
- **Disallow Untyped Defs**: true (except in tests/)
- **Plugins**: pydantic.mypy
- **Tests Override**: disallow_untyped_defs = false for tests/

## Code Patterns

### LangGraph Node Implementation
```python
async def node_name_node(state: TechSpecState) -> TechSpecState:
    """
    Brief description of what this node does.
    
    More detailed explanation if needed.
    
    Args:
        state: Current workflow state with required fields
    
    Returns:
        Updated state with new/modified fields
    """
    logger.info(
        "node_action_start",
        session_id=state["session_id"],
        additional_context="value"
    )
    
    try:
        # Implementation logic
        # ...
        
        # Update state
        state["field_name"] = value
        state["current_stage"] = "stage_name"
        state["completion_percentage"] = 50.0
        
        # Add conversation message
        state["conversation_history"].append({
            "role": "agent",
            "message": "User-facing message",
            "message_type": "success",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(
            "node_action_complete",
            session_id=state["session_id"],
            result_metrics="value"
        )
        
    except Exception as e:
        logger.error(
            "node_action_error",
            session_id=state["session_id"],
            error=str(e),
            exc_info=True
        )
        
        state["errors"].append({
            "node": "node_name",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": False
        })
        
        raise  # Re-raise if critical
    
    return state
```

### Docstrings
- **Required**: All public functions must have docstrings
- **Format**: Google style docstrings
- **Sections**: Brief description, detailed explanation, Args, Returns, Raises (if applicable)

### Type Hints
- **Required**: All function signatures must have type hints
- **Imports**: Use `from typing import` for complex types
- **State Annotations**: Use `Annotated[Type, operator.add]` for append-only state fields

### Logging
- **Logger**: Use structlog for structured logging
- **Pattern**: `logger = structlog.get_logger(__name__)` at module level
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Format**: `logger.info("action_name", key1=value1, key2=value2)`

### Error Handling
- **Pattern**: Try-except blocks with detailed error logging
- **State Tracking**: Append errors to `state["errors"]` list
- **Recovery**: Distinguish between recoverable and non-recoverable errors
- **Database Persistence**: Use `log_state_errors_to_db()` for error persistence

## File Naming
- **Modules**: lowercase_with_underscores.py
- **Classes**: PascalCase
- **Functions**: lowercase_with_underscores
- **Constants**: UPPERCASE_WITH_UNDERSCORES

## Import Order (isort profile: black)
1. Standard library imports
2. Related third party imports
3. Local application/library specific imports
4. Each group separated by blank line

## Testing Conventions
- **Test Files**: `test_*.py`
- **Test Classes**: `Test*`
- **Test Functions**: `test_*`
- **Async Tests**: Use `pytest-asyncio`, mode = "auto"
- **Coverage Target**: 80%+
