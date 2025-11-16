"""Monitoring and metrics module for Tech Spec Agent."""

from src.monitoring.metrics import (
    # API metrics
    api_requests_total,
    api_request_duration_seconds,
    # LLM metrics
    llm_requests_total,
    llm_tokens_used,
    llm_request_duration_seconds,
    llm_cost_usd,
    # Cache metrics
    cache_operations_total,
    cache_hit_ratio,
    track_cache_hit,
    track_cache_miss,
    track_cache_set,
    update_cache_hit_ratio,
    # Database metrics
    db_connections_active,
    db_connections_idle,
    db_query_duration_seconds,
    db_errors_total,
    # Workflow metrics
    workflow_sessions_total,
    workflow_duration_seconds,
    workflow_node_duration_seconds,
    workflow_node_errors_total,
    workflow_completion_percentage,
    track_workflow_node,
    # Tech research metrics
    tech_research_requests_total,
    tech_research_duration_seconds,
    # Document generation metrics
    doc_generation_requests_total,
    doc_generation_duration_seconds,
    trd_quality_score,
    # Code analysis metrics
    code_analysis_files_total,
    api_endpoints_inferred_total,
    # LLM tracking
    track_llm_usage,
)

__all__ = [
    "api_requests_total",
    "api_request_duration_seconds",
    "llm_requests_total",
    "llm_tokens_used",
    "llm_request_duration_seconds",
    "llm_cost_usd",
    "cache_operations_total",
    "cache_hit_ratio",
    "track_cache_hit",
    "track_cache_miss",
    "track_cache_set",
    "update_cache_hit_ratio",
    "db_connections_active",
    "db_connections_idle",
    "db_query_duration_seconds",
    "db_errors_total",
    "workflow_sessions_total",
    "workflow_duration_seconds",
    "workflow_node_duration_seconds",
    "workflow_node_errors_total",
    "workflow_completion_percentage",
    "track_workflow_node",
    "tech_research_requests_total",
    "tech_research_duration_seconds",
    "doc_generation_requests_total",
    "doc_generation_duration_seconds",
    "trd_quality_score",
    "code_analysis_files_total",
    "api_endpoints_inferred_total",
    "track_llm_usage",
]
