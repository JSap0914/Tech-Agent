"""
Code analysis nodes for parsing Google AI Studio code and inferring API specifications.

These nodes analyze React/TypeScript code to extract component structure,
API calls, and data models to supplement the TRD generation.

Week 9 Enhancements:
- AST-like parsing for more accurate code analysis
- GraphQL query/mutation detection and parsing
- Improved type inference from TypeScript interfaces
"""

import os
import re
import json
import zipfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import structlog

from src.langgraph.state import TechSpecState

logger = structlog.get_logger()


async def parse_ai_studio_code_node(state: TechSpecState) -> TechSpecState:
    """
    Parse Google AI Studio generated code ZIP file.

    Extracts:
    - React component structure
    - Props interfaces
    - State variables
    - Event handlers
    - Child components

    Updates state with parsed component data for API inference.
    If no code is provided, gracefully skips this step.
    """
    logger.info(
        "parse_ai_studio_code_start",
        session_id=state["session_id"],
        has_code_path=bool(state.get("google_ai_studio_code_path"))
    )

    try:
        # Check if Google AI Studio code path exists
        code_path = state.get("google_ai_studio_code_path")

        if not code_path:
            logger.info(
                "no_ai_studio_code",
                session_id=state["session_id"],
                message="No Google AI Studio code provided, skipping code analysis"
            )

            state["conversation_history"].append({
                "role": "agent",
                "message": (
                    "ℹ️ No Google AI Studio code was provided for this project. "
                    "API specifications will be inferred from PRD and design documents only."
                ),
                "message_type": "info",
                "timestamp": datetime.now().isoformat()
            })

            state["current_stage"] = "code_analysis_skipped"
            state["completion_percentage"] = 55.0

            return state

        # Verify file exists
        if not os.path.exists(code_path):
            raise FileNotFoundError(f"Google AI Studio code file not found: {code_path}")

        # Extract ZIP file
        extract_dir = code_path.replace(".zip", "_extracted")

        if not os.path.exists(extract_dir):
            with zipfile.ZipFile(code_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.info("code_extracted", extract_dir=extract_dir)

        # Find all component files (.tsx, .jsx, .ts, .js)
        component_files = _find_component_files(extract_dir)
        logger.info("components_found", count=len(component_files))

        # Parse each component (Week 9: Use enhanced parser)
        parsed_components = []
        for file_path in component_files:
            try:
                # Try enhanced parser first (AST-like + GraphQL)
                component_data = _parse_component_file_enhanced(file_path)
                if component_data:
                    parsed_components.append(component_data)
            except Exception as e:
                logger.warning("component_parse_error", file=file_path, error=str(e))
                continue

        # Update state with parsed data
        state["google_ai_studio_data"] = {
            "code_path": code_path,
            "extract_dir": extract_dir,
            "components": parsed_components,
            "total_components": len(parsed_components),
            "parsed_at": datetime.now().isoformat()
        }

        state["conversation_history"].append({
            "role": "agent",
            "message": (
                f"✅ Successfully analyzed Google AI Studio code\n\n"
                f"Found {len(parsed_components)} React components:\n"
                + "\n".join([f"  • {comp['name']}" for comp in parsed_components[:5]])
                + (f"\n  ... and {len(parsed_components) - 5} more" if len(parsed_components) > 5 else "")
            ),
            "message_type": "analysis_result",
            "timestamp": datetime.now().isoformat()
        })

        state["current_stage"] = "code_parsed"
        state["completion_percentage"] = 55.0

        logger.info(
            "parse_ai_studio_code_complete",
            session_id=state["session_id"],
            components_parsed=len(parsed_components)
        )

    except Exception as e:
        logger.error(
            "parse_ai_studio_code_error",
            session_id=state["session_id"],
            error=str(e),
            exc_info=True
        )

        state["errors"].append({
            "node": "parse_ai_studio_code",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Gracefully degrade - continue without code analysis
        state["conversation_history"].append({
            "role": "agent",
            "message": (
                f"⚠️ Warning: Failed to parse Google AI Studio code ({type(e).__name__}). "
                "Continuing with API inference from design documents only."
            ),
            "message_type": "warning",
            "timestamp": datetime.now().isoformat()
        })

        state["current_stage"] = "code_analysis_failed"
        state["completion_percentage"] = 55.0

    return state


async def infer_api_spec_node(state: TechSpecState) -> TechSpecState:
    """
    Infer API specification from parsed components and design documents.

    Analyzes:
    - fetch() and axios API calls in components
    - Props interfaces (likely represent API response types)
    - State variables (data that comes from backend)
    - Form submissions (request bodies)

    Generates preliminary API endpoint list for TRD generation.
    """
    logger.info(
        "infer_api_spec_start",
        session_id=state["session_id"],
        has_parsed_code=bool(state.get("google_ai_studio_data"))
    )

    try:
        inferred_endpoints = []
        graphql_endpoints = []

        # Check if we have parsed code
        if state.get("google_ai_studio_data"):
            components = state["google_ai_studio_data"].get("components", [])

            # Analyze each component for API calls (REST and GraphQL)
            for component in components:
                # Extract REST API endpoints
                component_endpoints = _extract_api_calls_from_component(component)
                inferred_endpoints.extend(component_endpoints)

                # Week 9: Extract GraphQL endpoints
                if component.get("uses_graphql") and component.get("graphql_operations"):
                    graphql_ops = _graphql_to_rest_endpoints(component["graphql_operations"])
                    graphql_endpoints.extend(graphql_ops)
                    logger.info(
                        "graphql_operations_found",
                        component=component["name"],
                        operations=len(component["graphql_operations"])
                    )

        # Combine REST and GraphQL endpoints
        inferred_endpoints.extend(graphql_endpoints)

        # Fallback: Infer from design documents if no code available
        if not inferred_endpoints and state.get("design_docs"):
            inferred_endpoints = _infer_apis_from_design_docs(state["design_docs"])

        # Remove duplicate endpoints
        unique_endpoints = _deduplicate_endpoints(inferred_endpoints)

        # Update state (FIXED: Use "inferred_apis" to match state schema)
        # Store endpoints list directly (what downstream nodes expect)
        state["inferred_apis"] = unique_endpoints

        # Store enhanced metadata in code_analysis_summary
        state["code_analysis_summary"] = {
            "total_endpoints": len(unique_endpoints),
            "rest_endpoints": len(inferred_endpoints) - len(graphql_endpoints),
            "graphql_endpoints": len(graphql_endpoints),
            "inferred_from": "code" if state.get("google_ai_studio_data") else "design_docs",
            "inferred_at": datetime.now().isoformat(),
            "week9_enhanced": True  # Marker for Week 9 enhancements
        }

        # Add conversation message (Week 9: Show GraphQL info)
        if unique_endpoints:
            metadata = state.get("code_analysis_summary", {})
            rest_count = metadata.get("rest_endpoints", 0)
            graphql_count = metadata.get("graphql_endpoints", 0)

            # Format endpoint list
            endpoint_list = "\n".join([
                f"  • {ep['method']} {ep['path']}" +
                (f" (GraphQL: {ep.get('graphql_operation', '')})" if ep.get('graphql_operation') else "")
                for ep in unique_endpoints[:10]
            ])
            more_text = f"\n  ... and {len(unique_endpoints) - 10} more" if len(unique_endpoints) > 10 else ""

            # Build summary
            summary = f"✅ Inferred {len(unique_endpoints)} API endpoints"
            if graphql_count > 0:
                summary += f" ({rest_count} REST, {graphql_count} GraphQL)"
            summary += ":\n\n"

            state["conversation_history"].append({
                "role": "agent",
                "message": (
                    f"{summary}"
                    f"{endpoint_list}{more_text}\n\n"
                    "These will be detailed in the TRD generation."
                ),
                "message_type": "api_inference",
                "timestamp": datetime.now().isoformat()
            })
        else:
            state["conversation_history"].append({
                "role": "agent",
                "message": (
                    "ℹ️ No API endpoints could be automatically inferred. "
                    "API specification will be generated based on PRD requirements."
                ),
                "message_type": "info",
                "timestamp": datetime.now().isoformat()
            })

        state["current_stage"] = "api_inferred"
        state["completion_percentage"] = 60.0

        logger.info(
            "infer_api_spec_complete",
            session_id=state["session_id"],
            endpoints_inferred=len(unique_endpoints)
        )

    except Exception as e:
        logger.error(
            "infer_api_spec_error",
            session_id=state["session_id"],
            error=str(e),
            exc_info=True
        )

        state["errors"].append({
            "node": "infer_api_spec",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        })

        # Continue without inferred API spec
        state["current_stage"] = "api_inference_failed"
        state["completion_percentage"] = 60.0

    return state


# Helper functions

def _find_component_files(directory: str) -> List[str]:
    """Find all React/TypeScript component files."""
    component_files = []
    extensions = ('.tsx', '.jsx', '.ts', '.js')

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extensions) and not file.endswith('.test.tsx') and not file.endswith('.test.ts'):
                component_files.append(os.path.join(root, file))

    return component_files


def _parse_component_file(file_path: str) -> Optional[Dict]:
    """
    Parse a single component file to extract structure.

    Uses regex patterns to extract:
    - Component name
    - Props interface
    - API calls (fetch, axios)
    - State variables
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract component name
        component_name_match = re.search(
            r'(?:export\s+(?:default\s+)?)?(?:function|const)\s+(\w+)',
            content
        )
        component_name = component_name_match.group(1) if component_name_match else os.path.basename(file_path)

        # Extract props interface
        props_interface = _extract_props_interface(content, component_name)

        # Extract API calls
        api_calls = _extract_api_calls(content)

        # Extract state variables
        state_vars = _extract_state_variables(content)

        return {
            "name": component_name,
            "file_path": file_path,
            "props_interface": props_interface,
            "api_calls": api_calls,
            "state_variables": state_vars
        }

    except Exception as e:
        logger.warning("component_file_parse_error", file=file_path, error=str(e))
        return None


def _extract_props_interface(content: str, component_name: str) -> Dict:
    """Extract TypeScript props interface."""
    interface_pattern = rf'interface\s+{component_name}Props\s*{{([^}}]+)}}'
    match = re.search(interface_pattern, content, re.DOTALL)

    if match:
        props_content = match.group(1)
        props = {}

        # Parse individual properties
        prop_pattern = r'(\w+)\??\s*:\s*([^;,\n]+)'
        for prop_match in re.finditer(prop_pattern, props_content):
            prop_name = prop_match.group(1)
            prop_type = prop_match.group(2).strip()
            props[prop_name] = prop_type

        return props

    return {}


def _extract_api_calls(content: str) -> List[Dict]:
    """
    Extract fetch() and axios API calls using enhanced AST-like parsing.

    Week 9: Now uses _extract_function_calls for better accuracy.
    """
    api_calls = []

    # Week 9: Use enhanced function call extraction
    fetch_calls = _extract_function_calls(content, ['fetch'])
    axios_get_calls = _extract_function_calls(content, ['axios.get'])
    axios_post_calls = _extract_function_calls(content, ['axios.post'])
    axios_put_calls = _extract_function_calls(content, ['axios.put'])
    axios_delete_calls = _extract_function_calls(content, ['axios.delete'])
    axios_patch_calls = _extract_function_calls(content, ['axios.patch'])

    # Process fetch() calls
    for call in fetch_calls:
        if len(call['arguments']) > 0:
            url = call['arguments'][0].strip('\'"` ')
            method = "GET"  # Default

            # Check if second argument has method
            if len(call['arguments']) > 1:
                options = call['arguments'][1]
                method_match = re.search(r'method\s*:\s*[`\'"](\w+)[`\'"]', options)
                if method_match:
                    method = method_match.group(1).upper()

            api_calls.append({
                "type": "fetch",
                "url": url,
                "method": method
            })

    # Process axios calls
    for method_name, calls in [
        ('GET', axios_get_calls),
        ('POST', axios_post_calls),
        ('PUT', axios_put_calls),
        ('DELETE', axios_delete_calls),
        ('PATCH', axios_patch_calls)
    ]:
        for call in calls:
            if len(call['arguments']) > 0:
                url = call['arguments'][0].strip('\'"` ')
                api_calls.append({
                    "type": "axios",
                    "url": url,
                    "method": method_name
                })

    return api_calls


def _extract_state_variables(content: str) -> List[Dict]:
    """Extract React state variables."""
    state_vars = []

    # useState pattern
    state_pattern = r'const\s+\[(\w+),\s*set\w+\]\s*=\s*useState(?:<([^>]+)>)?\s*\('
    for match in re.finditer(state_pattern, content):
        var_name = match.group(1)
        var_type = match.group(2) if match.group(2) else "unknown"

        state_vars.append({
            "name": var_name,
            "type": var_type
        })

    return state_vars


def _extract_api_calls_from_component(component: Dict) -> List[Dict]:
    """Convert component API calls to endpoint specifications."""
    endpoints = []

    for api_call in component.get("api_calls", []):
        endpoint = {
            "method": api_call["method"],
            "path": api_call["url"],
            "description": f"API endpoint used by {component['name']} component",
            "inferred_from": "component_code",
            "component": component["name"]
        }

        # Try to infer request/response types from props
        if component.get("props_interface"):
            endpoint["response_type"] = component["props_interface"]

        endpoints.append(endpoint)

    return endpoints


def _infer_apis_from_design_docs(design_docs: Dict[str, str]) -> List[Dict]:
    """
    Infer API endpoints from design document content.

    Looks for patterns like:
    - Lists of items (likely GET /items)
    - Forms (likely POST /items)
    - Detail views (likely GET /items/:id)
    - Delete buttons (likely DELETE /items/:id)
    """
    endpoints = []

    # Common patterns in design documents
    patterns = {
        r'(?:list|table|grid)\s+of\s+(\w+)': lambda m: {
            "method": "GET",
            "path": f"/api/{m.group(1).lower()}",
            "description": f"List {m.group(1)}",
            "inferred_from": "design_docs"
        },
        r'(?:create|add)\s+(?:new\s+)?(\w+)\s+form': lambda m: {
            "method": "POST",
            "path": f"/api/{m.group(1).lower()}",
            "description": f"Create {m.group(1)}",
            "inferred_from": "design_docs"
        },
        r'(?:edit|update)\s+(\w+)\s+form': lambda m: {
            "method": "PUT",
            "path": f"/api/{m.group(1).lower()}/:id",
            "description": f"Update {m.group(1)}",
            "inferred_from": "design_docs"
        },
        r'delete\s+(\w+)\s+button': lambda m: {
            "method": "DELETE",
            "path": f"/api/{m.group(1).lower()}/:id",
            "description": f"Delete {m.group(1)}",
            "inferred_from": "design_docs"
        }
    }

    for doc_type, content in design_docs.items():
        for pattern, endpoint_factory in patterns.items():
            for match in re.finditer(pattern, content, re.IGNORECASE):
                try:
                    endpoint = endpoint_factory(match)
                    endpoints.append(endpoint)
                except Exception:
                    continue

    return endpoints


def _deduplicate_endpoints(endpoints: List[Dict]) -> List[Dict]:
    """Remove duplicate endpoints based on method + path."""
    seen = set()
    unique = []

    for endpoint in endpoints:
        key = (endpoint["method"], endpoint["path"])
        if key not in seen:
            seen.add(key)
            unique.append(endpoint)

    return unique


# ============= Week 9: Enhanced AST-like Parsing =============

def _parse_typescript_interface(content: str, interface_name: str) -> Dict:
    """
    Parse TypeScript interface with AST-like accuracy.

    Handles:
    - Nested objects
    - Array types
    - Optional properties
    - Union types
    - Generic types
    """
    # Find the interface definition
    interface_pattern = rf'interface\s+{re.escape(interface_name)}\s*{{([^}}]*)(?:}})'
    match = re.search(interface_pattern, content, re.DOTALL)

    if not match:
        return {}

    interface_body = match.group(1)
    properties = {}

    # Parse each property with better type detection
    # Matches: propertyName?: Type | Type[]  or propertyName: { nested: Type }
    prop_pattern = r'(\w+)(\?)?:\s*([^;,\n]+)'

    for prop_match in re.finditer(prop_pattern, interface_body):
        prop_name = prop_match.group(1)
        optional = bool(prop_match.group(2))
        prop_type_raw = prop_match.group(3).strip()

        # Parse type more accurately
        prop_type = _parse_typescript_type(prop_type_raw)

        properties[prop_name] = {
            "type": prop_type,
            "optional": optional,
            "raw_type": prop_type_raw
        }

    return properties


def _parse_typescript_type(type_str: str) -> str:
    """
    Parse TypeScript type string into structured format.

    Handles:
    - Primitives: string, number, boolean
    - Arrays: string[], Array<string>
    - Objects: { key: value }
    - Unions: string | number
    - Generics: Promise<User>, Array<Item>
    """
    type_str = type_str.strip()

    # Array types
    if type_str.endswith('[]'):
        return f"Array<{type_str[:-2]}>"

    # Generic types
    generic_match = re.match(r'(\w+)<([^>]+)>', type_str)
    if generic_match:
        container = generic_match.group(1)
        inner_type = generic_match.group(2)
        return f"{container}<{inner_type}>"

    # Union types
    if '|' in type_str:
        return f"Union<{type_str}>"

    # Object types (inline)
    if type_str.startswith('{'):
        return "Object"

    return type_str


def _extract_function_calls(content: str, function_names: List[str]) -> List[Dict]:
    """
    Extract function calls with AST-like precision.

    Args:
        content: Source code content
        function_names: List of function names to search for (e.g., ['fetch', 'axios.get'])

    Returns:
        List of function call details with arguments
    """
    function_calls = []

    for func_name in function_names:
        # Pattern to match function calls with arguments
        # Handles: func(arg1, arg2) and obj.func(arg1, arg2)
        pattern = rf'{re.escape(func_name)}\s*\(([^)]*)\)'

        for match in re.finditer(pattern, content):
            args_str = match.group(1)

            # Parse arguments (simplified - handles strings and basic expressions)
            args = _parse_function_arguments(args_str)

            function_calls.append({
                "function": func_name,
                "arguments": args,
                "raw_args": args_str,
                "position": match.start()
            })

    return function_calls


def _parse_function_arguments(args_str: str) -> List[str]:
    """
    Parse function arguments from string.

    Handles:
    - String literals: 'text', "text", `template ${var}`
    - Variables: varName
    - Objects: { key: value }
    """
    args = []

    # Split by commas, but respect nested structures
    depth = 0
    current_arg = []

    for char in args_str:
        if char in '{[(':
            depth += 1
        elif char in '}])':
            depth -= 1
        elif char == ',' and depth == 0:
            args.append(''.join(current_arg).strip())
            current_arg = []
            continue

        current_arg.append(char)

    # Add last argument
    if current_arg:
        args.append(''.join(current_arg).strip())

    return [arg for arg in args if arg]


def _extract_imports(content: str) -> Dict[str, List[str]]:
    """
    Extract import statements with package and imported items.

    Returns:
        {
            "package_name": ["imported", "items"],
            ...
        }
    """
    imports = {}

    # Combined pattern for mixed imports: import React, { useState } from 'react'
    mixed_import_pattern = r'import\s+(\w+)\s*,\s*\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(mixed_import_pattern, content):
        default_item = match.group(1)
        named_items = [item.strip() for item in match.group(2).split(',')]
        package = match.group(3)
        imports[package] = [default_item] + named_items

    # import { A, B } from 'package' (only if not already matched by mixed pattern)
    named_import_pattern = r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(named_import_pattern, content):
        items = [item.strip() for item in match.group(1).split(',')]
        package = match.group(2)
        if package not in imports:
            imports[package] = items

    # import A from 'package' (only if not already matched)
    default_import_pattern = r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(default_import_pattern, content):
        item = match.group(1)
        package = match.group(2)
        if package not in imports:
            imports[package] = [item]

    # import * as Name from 'package'
    namespace_import_pattern = r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(namespace_import_pattern, content):
        namespace = match.group(1)
        package = match.group(2)
        imports[package] = [f"* as {namespace}"]

    return imports


# ============= Week 9: GraphQL Support =============

def _detect_graphql_usage(content: str) -> bool:
    """
    Detect if the file uses GraphQL.

    Checks for:
    - Apollo Client imports
    - useQuery, useMutation hooks
    - gql template literals
    - @apollo/client package
    """
    graphql_indicators = [
        r'@apollo/client',
        r'graphql-request',
        r'urql',
        r'\buseQuery\b',
        r'\buseMutation\b',
        r'\buse(Lazy)?Query\b',
        r'\bgql`',
        r'import.*gql.*from',
    ]

    for indicator in graphql_indicators:
        if re.search(indicator, content):
            return True

    return False


def _extract_graphql_operations(content: str) -> List[Dict]:
    """
    Extract GraphQL queries and mutations from code.

    Returns:
        List of {
            "type": "query" | "mutation",
            "name": "OperationName",
            "query": "full GraphQL query string",
            "variables": ["var1", "var2"],
            "fields": ["field1", "field2"]
        }
    """
    operations = []

    # Pattern to match gql`` template literals (fixed to handle multiline with nested braces)
    gql_pattern = r'gql`\s*(query|mutation)\s+(\w+)\s*(\([^)]*\))?\s*\{([^`]+)`'

    for match in re.finditer(gql_pattern, content, re.DOTALL):
        operation_type = match.group(1)
        operation_name = match.group(2)
        variables_str = match.group(3) or ""
        query_body = match.group(4)

        # Extract variable names from ($var1: Type, $var2: Type)
        variables = re.findall(r'\$(\w+)', variables_str)

        # Extract top-level fields from query body
        fields = _extract_graphql_fields(query_body)

        operations.append({
            "type": operation_type,
            "name": operation_name,
            "query": match.group(0),
            "variables": variables,
            "fields": fields,
            "inferred_endpoint": f"GraphQL {operation_type.upper()}: {operation_name}"
        })

    return operations


def _extract_graphql_fields(query_body: str) -> List[str]:
    """
    Extract field names from GraphQL query body.

    Example:
        user { id name email } → ['user', 'id', 'name', 'email']
    """
    # Remove comments
    query_body = re.sub(r'#.*$', '', query_body, flags=re.MULTILINE)

    # Extract all identifiers (word boundaries)
    field_pattern = r'\b(\w+)\b'
    fields = re.findall(field_pattern, query_body)

    # Filter out GraphQL keywords, common type names, and single letters
    graphql_keywords = {
        'query', 'mutation', 'subscription', 'fragment', 'on', '__typename',
        'ID', 'String', 'Int', 'Float', 'Boolean',  # Common GraphQL types
        'type', 'input', 'enum', 'interface', 'union', 'scalar'  # Schema definition keywords
    }
    fields = [f for f in fields if f not in graphql_keywords]

    return fields


def _graphql_to_rest_endpoints(operations: List[Dict]) -> List[Dict]:
    """
    Convert GraphQL operations to REST-like endpoint specifications for TRD.

    This helps document the API even when using GraphQL.
    """
    endpoints = []

    for op in operations:
        endpoint = {
            "method": "POST",  # GraphQL typically uses POST
            "path": "/graphql",
            "graphql_operation": op["name"],
            "graphql_type": op["type"],
            "description": f"GraphQL {op['type']}: {op['name']}",
            "request_body": {
                "query": op["query"],
                "variables": {var: "..." for var in op["variables"]}
            },
            "response_fields": op["fields"],
            "inferred_from": "graphql_code"
        }

        endpoints.append(endpoint)

    return endpoints


# ============= Enhanced Component Parsing =============

def _parse_component_file_enhanced(file_path: str) -> Optional[Dict]:
    """
    Enhanced component parsing with AST-like precision and GraphQL support.

    Improvements over original:
    - Better TypeScript interface parsing
    - GraphQL query/mutation detection
    - Import analysis
    - More accurate API call extraction
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract component name
        component_name_match = re.search(
            r'(?:export\s+(?:default\s+)?)?(?:function|const)\s+(\w+)',
            content
        )
        component_name = component_name_match.group(1) if component_name_match else os.path.basename(file_path)

        # Extract imports
        imports = _extract_imports(content)

        # Detect GraphQL usage
        uses_graphql = _detect_graphql_usage(content)

        # Extract props interface (enhanced)
        props_interface = _parse_typescript_interface(content, f"{component_name}Props")

        # Extract API calls (REST)
        rest_api_calls = _extract_api_calls(content)

        # Extract GraphQL operations if applicable
        graphql_operations = []
        if uses_graphql:
            graphql_operations = _extract_graphql_operations(content)

        # Extract state variables
        state_vars = _extract_state_variables(content)

        # Extract hooks usage
        hooks = _extract_hooks_usage(content)

        return {
            "name": component_name,
            "file_path": file_path,
            "imports": imports,
            "uses_graphql": uses_graphql,
            "props_interface": props_interface,
            "api_calls": rest_api_calls,
            "graphql_operations": graphql_operations,
            "state_variables": state_vars,
            "hooks": hooks,
            "parsing_method": "ast_enhanced"  # Week 9 marker
        }

    except Exception as e:
        logger.warning("enhanced_component_parse_error", file=file_path, error=str(e))
        # Fallback to original parser
        return _parse_component_file(file_path)


def _extract_hooks_usage(content: str) -> List[str]:
    """
    Extract React hooks used in the component.

    Returns:
        List of hook names: ['useState', 'useEffect', 'useQuery', ...]
    """
    hooks = []

    # Pattern to match use* function calls
    hook_pattern = r'\b(use\w+)\s*\('

    for match in re.finditer(hook_pattern, content):
        hook_name = match.group(1)
        if hook_name not in hooks:
            hooks.append(hook_name)

    return hooks
