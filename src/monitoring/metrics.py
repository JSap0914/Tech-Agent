"""
Prometheus metrics for Tech Spec Agent performance monitoring.
Week 12: Performance optimization and monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
import structlog

logger = structlog.get_logger(__name__)

# ============= API Metrics =============

# Request metrics
api_requests_total = Counter(
    "tech_spec_api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"]
)

api_request_duration_seconds = Histogram(
    "tech_spec_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# ============= LLM Metrics =============

llm_requests_total = Counter(
    "tech_spec_llm_requests_total",
    "Total number of LLM API requests",
    ["model", "operation"]
)

llm_tokens_used = Counter(
    "tech_spec_llm_tokens_used_total",
    "Total number of LLM tokens used",
    ["model", "token_type"]  # token_type: input, output
)

llm_request_duration_seconds = Histogram(
    "tech_spec_llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model", "operation"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

llm_cost_usd = Counter(
    "tech_spec_llm_cost_usd_total",
    "Total LLM cost in USD",
    ["model"]
)

# ============= Cache Metrics =============

cache_operations_total = Counter(
    "tech_spec_cache_operations_total",
    "Total number of cache operations",
    ["operation", "result"]  # operation: get/set/delete, result: hit/miss/error
)

cache_hit_ratio = Gauge(
    "tech_spec_cache_hit_ratio",
    "Cache hit ratio (0-1)"
)

cache_size_bytes = Gauge(
    "tech_spec_cache_size_bytes",
    "Current cache size in bytes"
)

# ============= Database Metrics =============

db_connections_active = Gauge(
    "tech_spec_db_connections_active",
    "Number of active database connections"
)

db_connections_idle = Gauge(
    "tech_spec_db_connections_idle",
    "Number of idle database connections"
)

db_query_duration_seconds = Histogram(
    "tech_spec_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_errors_total = Counter(
    "tech_spec_db_errors_total",
    "Total number of database errors",
    ["operation", "error_type"]
)

# ============= Workflow Metrics =============

workflow_sessions_total = Counter(
    "tech_spec_workflow_sessions_total",
    "Total number of workflow sessions started",
    ["status"]  # status: started, completed, failed, aborted
)

workflow_duration_seconds = Histogram(
    "tech_spec_workflow_duration_seconds",
    "Total workflow duration in seconds",
    buckets=(60, 300, 600, 900, 1200, 1800, 3600)  # 1min to 1hour
)

workflow_node_duration_seconds = Histogram(
    "tech_spec_workflow_node_duration_seconds",
    "Duration of individual workflow nodes in seconds",
    ["node_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

workflow_node_errors_total = Counter(
    "tech_spec_workflow_node_errors_total",
    "Total number of workflow node errors",
    ["node_name", "error_type"]
)

workflow_current_stage = Gauge(
    "tech_spec_workflow_current_stage",
    "Current workflow stage (encoded as integer)",
    ["session_id"]
)

workflow_completion_percentage = Gauge(
    "tech_spec_workflow_completion_percentage",
    "Workflow completion percentage (0-100)",
    ["session_id"]
)

# ============= Technology Research Metrics =============

tech_research_requests_total = Counter(
    "tech_spec_tech_research_requests_total",
    "Total number of technology research requests",
    ["category"]
)

tech_research_duration_seconds = Histogram(
    "tech_spec_tech_research_duration_seconds",
    "Technology research duration in seconds",
    ["category"],
    buckets=(1.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

tech_research_web_searches_total = Counter(
    "tech_spec_tech_research_web_searches_total",
    "Total number of web searches performed",
    ["category"]
)

# ============= Document Generation Metrics =============

doc_generation_requests_total = Counter(
    "tech_spec_doc_generation_requests_total",
    "Total number of document generation requests",
    ["document_type"]  # trd, api_spec, db_schema, architecture, tech_stack
)

doc_generation_duration_seconds = Histogram(
    "tech_spec_doc_generation_duration_seconds",
    "Document generation duration in seconds",
    ["document_type"],
    buckets=(5.0, 10.0, 20.0, 30.0, 60.0, 120.0)
)

trd_quality_score = Histogram(
    "tech_spec_trd_quality_score",
    "TRD quality scores distribution",
    buckets=(50, 60, 70, 75, 80, 85, 90, 92, 95, 98, 100)
)

trd_validation_iterations = Histogram(
    "tech_spec_trd_validation_iterations",
    "Number of TRD generation iterations before passing validation",
    buckets=(1, 2, 3)
)

# ============= Code Analysis Metrics =============

code_analysis_files_total = Counter(
    "tech_spec_code_analysis_files_total",
    "Total number of code files analyzed",
    ["file_type"]  # tsx, ts, jsx, js
)

code_analysis_components_total = Counter(
    "tech_spec_code_analysis_components_total",
    "Total number of React components parsed"
)

api_endpoints_inferred_total = Counter(
    "tech_spec_api_endpoints_inferred_total",
    "Total number of API endpoints inferred",
    ["endpoint_type"]  # rest, graphql
)

code_analysis_duration_seconds = Histogram(
    "tech_spec_code_analysis_duration_seconds",
    "Code analysis duration in seconds",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0)
)

# ============= WebSocket Metrics =============

websocket_connections_active = Gauge(
    "tech_spec_websocket_connections_active",
    "Number of active WebSocket connections"
)

websocket_messages_total = Counter(
    "tech_spec_websocket_messages_total",
    "Total number of WebSocket messages",
    ["direction"]  # sent, received
)

# ============= User Decision Metrics =============

user_decisions_total = Counter(
    "tech_spec_user_decisions_total",
    "Total number of user technology decisions",
    ["category", "decision_type"]  # decision_type: option_selected, ai_recommended, custom_search
)

user_decision_duration_seconds = Summary(
    "tech_spec_user_decision_duration_seconds",
    "Time taken for user to make a decision",
    ["category"]
)


# ============= Helper Functions =============

def track_cache_hit():
    """Track cache hit."""
    cache_operations_total.labels(operation="get", result="hit").inc()


def track_cache_miss():
    """Track cache miss."""
    cache_operations_total.labels(operation="get", result="miss").inc()


def track_cache_set(success: bool = True):
    """Track cache set operation."""
    result = "success" if success else "error"
    cache_operations_total.labels(operation="set", result=result).inc()


def update_cache_hit_ratio(hits: int, total: int):
    """Update cache hit ratio gauge."""
    if total > 0:
        ratio = hits / total
        cache_hit_ratio.set(ratio)


def track_llm_usage(model: str, input_tokens: int, output_tokens: int, cost_usd: float = 0.0):
    """
    Track LLM usage metrics.

    Args:
        model: Model name (e.g., "claude-sonnet-4")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Cost in USD (optional)
    """
    llm_tokens_used.labels(model=model, token_type="input").inc(input_tokens)
    llm_tokens_used.labels(model=model, token_type="output").inc(output_tokens)

    if cost_usd > 0:
        llm_cost_usd.labels(model=model).inc(cost_usd)


def track_workflow_node(node_name: str, duration_seconds: float, error: str = None):
    """
    Track workflow node execution.

    Args:
        node_name: Name of the workflow node
        duration_seconds: Execution duration
        error: Error type if node failed
    """
    workflow_node_duration_seconds.labels(node_name=node_name).observe(duration_seconds)

    if error:
        workflow_node_errors_total.labels(node_name=node_name, error_type=error).inc()


logger.info("Prometheus metrics initialized")
