import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 1. HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "deva_http_requests_total",
    "Total HTTP requests processed by DEVA Intelligence",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "deva_http_request_duration_seconds",
    "Histogram of HTTP request latencies in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# 2. Search & Retrieval Metrics
SEARCH_LATENCY_SECONDS = Histogram(
    "deva_search_latency_seconds",
    "Histogram of dual-path search and reranking execution latency",
    ["mode"],
    buckets=[0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)

SEARCH_CACHE_HITS_TOTAL = Counter(
    "deva_search_cache_hits_total",
    "Total search cache lookups categorized by hit or miss",
    ["result"],  # hit | miss
)

# 3. Ingestion Metrics
INGESTION_RECORDS_TOTAL = Counter(
    "deva_ingestion_records_total",
    "Total raw records parsed and normalized through ingestion adapters",
    ["adapter_key", "status"],  # inserted | updated | quarantined
)

# 4. Agent & LLM Metrics
AGENT_TOKENS_TOTAL = Counter(
    "deva_agent_tokens_total",
    "Total prompt and completion tokens processed by multi-agent swarms",
    ["workflow_type", "token_type"],  # prompt | completion
)

AGENT_RUNS_TOTAL = Counter(
    "deva_agent_runs_total",
    "Total multi-agent workflow executions",
    ["workflow_type", "status"],  # completed | failed
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/metrics", "/api/v1/health/live"):
            return await call_next(request)

        method = request.method
        path = request.url.path
        # Normalize paths with UUIDs or query strings
        if path.startswith("/api/v1/intel/documents/"):
            normalized_path = "/api/v1/intel/documents/{id}"
        elif path.startswith("/api/v1/users/me/"):
            normalized_path = "/api/v1/users/me/{subpath}"
        else:
            normalized_path = path

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration = time.perf_counter() - start_time
            HTTP_REQUESTS_TOTAL.labels(method=method, path=normalized_path, status_code=str(response.status_code)).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=normalized_path).observe(duration)
            return response
        except Exception as exc:
            duration = time.perf_counter() - start_time
            HTTP_REQUESTS_TOTAL.labels(method=method, path=normalized_path, status_code="500").inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=normalized_path).observe(duration)
            raise exc


def get_metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
