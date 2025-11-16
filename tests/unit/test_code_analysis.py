"""
Unit tests for code analysis enhancements (Week 9).
Tests AST-like parsing, GraphQL detection, and API inference.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.langgraph.nodes.code_analysis_nodes import (
    _parse_typescript_interface,
    _extract_function_calls,
    _parse_function_arguments,
    _extract_imports,
    _detect_graphql_usage,
    _extract_graphql_operations,
    _extract_graphql_fields,
    _graphql_to_rest_endpoints,
    _extract_hooks_usage,
    _extract_api_calls,
)


class TestTypescriptInterfaceParsing:
    """Test TypeScript interface parsing with AST-like accuracy."""

    def test_parse_simple_interface(self):
        """Test parsing simple TypeScript interface."""
        content = """
        interface UserProps {
            id: string;
            name: string;
            age: number;
        }
        """

        result = _parse_typescript_interface(content, "UserProps")

        assert "id" in result
        assert result["id"]["type"] == "string"
        assert result["id"]["optional"] is False

        assert "name" in result
        assert result["name"]["type"] == "string"

        assert "age" in result
        assert result["age"]["type"] == "number"

    def test_parse_interface_with_optional_properties(self):
        """Test parsing interface with optional properties."""
        content = """
        interface UserProps {
            id: string;
            email?: string;
            phone?: string;
        }
        """

        result = _parse_typescript_interface(content, "UserProps")

        assert result["id"]["optional"] is False
        assert result["email"]["optional"] is True
        assert result["phone"]["optional"] is True

    def test_parse_interface_with_array_types(self):
        """Test parsing interface with array types."""
        content = """
        interface ComponentProps {
            tags: string[];
            items: Array<Item>;
        }
        """

        result = _parse_typescript_interface(content, "ComponentProps")

        assert "Array" in result["tags"]["type"]
        assert "Array" in result["items"]["type"]

    def test_parse_interface_with_generic_types(self):
        """Test parsing interface with generic types."""
        content = """
        interface DataProps {
            promise: Promise<User>;
            list: Array<string>;
            record: Record<string, any>;
        }
        """

        result = _parse_typescript_interface(content, "DataProps")

        assert "Promise" in result["promise"]["type"]
        assert "Array" in result["list"]["type"]
        assert "Record" in result["record"]["type"]

    def test_parse_interface_with_union_types(self):
        """Test parsing interface with union types."""
        content = """
        interface MixedProps {
            value: string | number;
            status: 'active' | 'inactive' | 'pending';
        }
        """

        result = _parse_typescript_interface(content, "MixedProps")

        assert "Union" in result["value"]["type"]
        assert "Union" in result["status"]["type"]

    def test_parse_nonexistent_interface(self):
        """Test parsing returns empty dict for non-existent interface."""
        content = """
        interface UserProps {
            id: string;
        }
        """

        result = _parse_typescript_interface(content, "NonExistentProps")

        assert result == {}


class TestFunctionCallExtraction:
    """Test enhanced function call extraction."""

    def test_extract_simple_function_calls(self):
        """Test extracting simple function calls."""
        content = """
        fetch('/api/users');
        axios.get('/api/posts');
        """

        fetch_calls = _extract_function_calls(content, ['fetch'])
        axios_calls = _extract_function_calls(content, ['axios.get'])

        assert len(fetch_calls) == 1
        assert fetch_calls[0]["function"] == "fetch"
        assert len(fetch_calls[0]["arguments"]) == 1

        assert len(axios_calls) == 1
        assert axios_calls[0]["function"] == "axios.get"

    def test_extract_function_calls_with_multiple_arguments(self):
        """Test extracting calls with multiple arguments."""
        content = """
        fetch('/api/users', { method: 'POST', body: JSON.stringify(data) });
        """

        calls = _extract_function_calls(content, ['fetch'])

        assert len(calls) == 1
        assert len(calls[0]["arguments"]) == 2
        # First argument is URL
        assert "'/api/users'" in calls[0]["arguments"][0]

    def test_extract_nested_function_calls(self):
        """Test extracting calls with nested structures."""
        content = """
        fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'John', age: 30 })
        });
        """

        calls = _extract_function_calls(content, ['fetch'])

        assert len(calls) == 1
        # Should have 2 arguments: URL and options object
        assert len(calls[0]["arguments"]) == 2

    def test_extract_multiple_function_calls(self):
        """Test extracting multiple calls to same function."""
        content = """
        fetch('/api/users');
        fetch('/api/posts');
        fetch('/api/comments');
        """

        calls = _extract_function_calls(content, ['fetch'])

        assert len(calls) == 3
        assert any('/api/users' in c["arguments"][0] for c in calls)
        assert any('/api/posts' in c["arguments"][0] for c in calls)
        assert any('/api/comments' in c["arguments"][0] for c in calls)


class TestFunctionArgumentParsing:
    """Test function argument parsing with nested structures."""

    def test_parse_simple_arguments(self):
        """Test parsing simple comma-separated arguments."""
        args_str = "'arg1', 'arg2', 'arg3'"

        result = _parse_function_arguments(args_str)

        assert len(result) == 3
        assert result[0].strip() == "'arg1'"
        assert result[1].strip() == "'arg2'"
        assert result[2].strip() == "'arg3'"

    def test_parse_arguments_with_objects(self):
        """Test parsing arguments containing objects."""
        args_str = "'/api/users', { method: 'POST', body: data }"

        result = _parse_function_arguments(args_str)

        assert len(result) == 2
        assert "'/api/users'" in result[0]
        assert "method: 'POST'" in result[1]
        assert "body: data" in result[1]

    def test_parse_arguments_with_nested_objects(self):
        """Test parsing arguments with deeply nested objects."""
        args_str = "url, { headers: { 'Content-Type': 'application/json' }, body: { name: 'John' } }"

        result = _parse_function_arguments(args_str)

        assert len(result) == 2
        # Second argument should contain both headers and body
        assert "headers" in result[1]
        assert "body" in result[1]

    def test_parse_arguments_with_arrays(self):
        """Test parsing arguments containing arrays."""
        args_str = "endpoint, { tags: ['tag1', 'tag2'], data: [1, 2, 3] }"

        result = _parse_function_arguments(args_str)

        assert len(result) == 2
        assert "tags" in result[1]
        assert "[1, 2, 3]" in result[1]

    def test_parse_empty_arguments(self):
        """Test parsing empty argument string."""
        args_str = ""

        result = _parse_function_arguments(args_str)

        assert result == []


class TestImportExtraction:
    """Test import statement extraction."""

    def test_extract_named_imports(self):
        """Test extracting named imports."""
        content = """
        import { useState, useEffect } from 'react';
        import { Button, Input } from '@/components';
        """

        result = _extract_imports(content)

        assert "react" in result
        assert "useState" in result["react"]
        assert "useEffect" in result["react"]

        assert "@/components" in result
        assert "Button" in result["@/components"]
        assert "Input" in result["@/components"]

    def test_extract_default_imports(self):
        """Test extracting default imports."""
        content = """
        import React from 'react';
        import axios from 'axios';
        """

        result = _extract_imports(content)

        assert "react" in result
        assert "React" in result["react"]

        assert "axios" in result
        assert "axios" in result["axios"]

    def test_extract_namespace_imports(self):
        """Test extracting namespace imports."""
        content = """
        import * as api from './api';
        import * as utils from '@/utils';
        """

        result = _extract_imports(content)

        assert "./api" in result
        assert "* as api" in result["./api"]

        assert "@/utils" in result
        assert "* as utils" in result["@/utils"]

    def test_extract_mixed_imports(self):
        """Test extracting mix of import types."""
        content = """
        import React, { useState } from 'react';
        import { useQuery } from '@apollo/client';
        import * as types from './types';
        """

        result = _extract_imports(content)

        assert len(result) >= 3


class TestGraphQLDetection:
    """Test GraphQL usage detection."""

    def test_detect_apollo_client(self):
        """Test detecting Apollo Client usage."""
        content = """
        import { useQuery, useMutation } from '@apollo/client';
        """

        result = _detect_graphql_usage(content)

        assert result is True

    def test_detect_graphql_request(self):
        """Test detecting graphql-request usage."""
        content = """
        import { request } from 'graphql-request';
        """

        result = _detect_graphql_usage(content)

        assert result is True

    def test_detect_gql_tag(self):
        """Test detecting gql template tag."""
        content = """
        const GET_USER = gql`
            query GetUser {
                user { id name }
            }
        `;
        """

        result = _detect_graphql_usage(content)

        assert result is True

    def test_detect_no_graphql(self):
        """Test no GraphQL detected in regular React code."""
        content = """
        import { useState } from 'react';

        function MyComponent() {
            const [state, setState] = useState(null);
            return <div>Hello</div>;
        }
        """

        result = _detect_graphql_usage(content)

        assert result is False


class TestGraphQLOperationExtraction:
    """Test GraphQL query/mutation extraction."""

    def test_extract_simple_query(self):
        """Test extracting simple GraphQL query."""
        content = """
        const GET_USERS = gql`
            query GetUsers {
                users {
                    id
                    name
                    email
                }
            }
        `;
        """

        result = _extract_graphql_operations(content)

        assert len(result) == 1
        assert result[0]["type"] == "query"
        assert result[0]["name"] == "GetUsers"
        assert "users" in result[0]["fields"]
        assert "id" in result[0]["fields"]
        assert "name" in result[0]["fields"]

    def test_extract_query_with_variables(self):
        """Test extracting query with variables."""
        content = """
        const GET_USER = gql`
            query GetUser($userId: ID!) {
                user(id: $userId) {
                    id
                    name
                }
            }
        `;
        """

        result = _extract_graphql_operations(content)

        assert len(result) == 1
        assert "userId" in result[0]["variables"]

    def test_extract_mutation(self):
        """Test extracting GraphQL mutation."""
        content = """
        const CREATE_USER = gql`
            mutation CreateUser($input: UserInput!) {
                createUser(input: $input) {
                    id
                    name
                }
            }
        `;
        """

        result = _extract_graphql_operations(content)

        assert len(result) == 1
        assert result[0]["type"] == "mutation"
        assert result[0]["name"] == "CreateUser"
        assert "input" in result[0]["variables"]

    def test_extract_multiple_operations(self):
        """Test extracting multiple GraphQL operations."""
        content = """
        const GET_USER = gql`query GetUser { user { id } }`;
        const UPDATE_USER = gql`mutation UpdateUser { updateUser { id } }`;
        """

        result = _extract_graphql_operations(content)

        assert len(result) == 2
        assert result[0]["type"] == "query"
        assert result[1]["type"] == "mutation"


class TestGraphQLFieldExtraction:
    """Test GraphQL field extraction."""

    def test_extract_simple_fields(self):
        """Test extracting simple field names."""
        query_body = """
        user {
            id
            name
            email
        }
        """

        result = _extract_graphql_fields(query_body)

        assert "user" in result
        assert "id" in result
        assert "name" in result
        assert "email" in result

    def test_extract_nested_fields(self):
        """Test extracting nested field names."""
        query_body = """
        user {
            id
            posts {
                title
                comments {
                    text
                }
            }
        }
        """

        result = _extract_graphql_fields(query_body)

        assert "user" in result
        assert "posts" in result
        assert "title" in result
        assert "comments" in result
        assert "text" in result

    def test_exclude_graphql_keywords(self):
        """Test that GraphQL keywords are excluded."""
        query_body = """
        query GetUser {
            user {
                id
                ... on Admin {
                    permissions
                }
            }
        }
        """

        result = _extract_graphql_fields(query_body)

        assert "query" not in result
        assert "on" not in result
        assert "user" in result
        assert "id" in result


class TestGraphQLToRESTConversion:
    """Test GraphQL to REST endpoint conversion."""

    def test_convert_query_to_rest(self):
        """Test converting GraphQL query to REST endpoint."""
        operations = [
            {
                "type": "query",
                "name": "GetUser",
                "query": "gql`query GetUser { user { id name } }`",
                "variables": ["userId"],
                "fields": ["user", "id", "name"]
            }
        ]

        result = _graphql_to_rest_endpoints(operations)

        assert len(result) == 1
        endpoint = result[0]

        assert endpoint["method"] == "POST"
        assert endpoint["path"] == "/graphql"
        assert endpoint["graphql_operation"] == "GetUser"
        assert endpoint["graphql_type"] == "query"
        assert "userId" in endpoint["request_body"]["variables"]
        assert endpoint["response_fields"] == ["user", "id", "name"]

    def test_convert_mutation_to_rest(self):
        """Test converting GraphQL mutation to REST endpoint."""
        operations = [
            {
                "type": "mutation",
                "name": "CreatePost",
                "query": "gql`mutation CreatePost { ... }`",
                "variables": ["input"],
                "fields": ["createPost", "id"]
            }
        ]

        result = _graphql_to_rest_endpoints(operations)

        assert len(result) == 1
        assert result[0]["graphql_type"] == "mutation"
        assert result[0]["graphql_operation"] == "CreatePost"


class TestHooksExtraction:
    """Test React hooks extraction."""

    def test_extract_standard_hooks(self):
        """Test extracting standard React hooks."""
        content = """
        function MyComponent() {
            const [state, setState] = useState(null);
            useEffect(() => {}, []);
            const context = useContext(MyContext);
        }
        """

        result = _extract_hooks_usage(content)

        assert "useState" in result
        assert "useEffect" in result
        assert "useContext" in result

    def test_extract_custom_hooks(self):
        """Test extracting custom hooks."""
        content = """
        function MyComponent() {
            const data = useCustomHook();
            const { loading } = useFetchData();
        }
        """

        result = _extract_hooks_usage(content)

        assert "useCustomHook" in result
        assert "useFetchData" in result

    def test_extract_third_party_hooks(self):
        """Test extracting third-party library hooks."""
        content = """
        function MyComponent() {
            const { data } = useQuery(QUERY);
            const [mutate] = useMutation(MUTATION);
            const router = useRouter();
        }
        """

        result = _extract_hooks_usage(content)

        assert "useQuery" in result
        assert "useMutation" in result
        assert "useRouter" in result


class TestAPICallExtraction:
    """Test API call extraction using enhanced parsing (Week 9 fix)."""

    def test_extract_fetch_get_call(self):
        """Test extracting simple GET fetch call."""
        content = """
        fetch('/api/users');
        """

        result = _extract_api_calls(content)

        assert len(result) == 1
        assert result[0]["type"] == "fetch"
        assert "/api/users" in result[0]["url"]
        assert result[0]["method"] == "GET"

    def test_extract_fetch_post_call(self):
        """Test extracting POST fetch call."""
        content = """
        fetch('/api/users', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        """

        result = _extract_api_calls(content)

        assert len(result) == 1
        assert result[0]["method"] == "POST"

    def test_extract_axios_calls(self):
        """Test extracting various axios calls."""
        content = """
        axios.get('/api/users');
        axios.post('/api/users', data);
        axios.put('/api/users/1', data);
        axios.delete('/api/users/1');
        """

        result = _extract_api_calls(content)

        assert len(result) == 4
        methods = [call["method"] for call in result]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_extract_api_calls_with_complex_arguments(self):
        """Test that enhanced parsing handles complex arguments correctly."""
        content = """
        fetch('/api/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name: 'John', data: { nested: true } })
        });
        """

        result = _extract_api_calls(content)

        # Should successfully parse despite complex nested structure
        assert len(result) == 1
        assert result[0]["method"] == "POST"
        assert "/api/users" in result[0]["url"]
