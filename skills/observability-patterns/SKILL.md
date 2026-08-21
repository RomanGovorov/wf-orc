---
name: observability-patterns
description: Observability — structured logging (structlog), distributed tracing (OpenTelemetry), metrics (Prometheus), health checks, SLO/SLI, profiling. Use when instrumenting code, configuring monitoring, or debugging production issues.
priority: 5
paths:
  - "**/logging*"
  - "**/tracing*"
  - "**/metrics*"
  - "**/monitoring*"
  - "**/health*"
  - "**/telemetry*"
  - "**/observability*"
---

# Observability Patterns

Complete guide to application observability — structured logging, distributed tracing, metrics collection, health checks, SLO/SLI implementation, alerting, and profiling.

## When to Use This Skill

- When instrumenting application code with logging, tracing, or metrics
- When configuring OpenTelemetry for distributed tracing
- When setting up Prometheus metrics collection
- When implementing health check endpoints (liveness, readiness, startup)
- When defining SLOs, SLIs, and error budgets
- When designing alerting rules (symptom-based vs cause-based)
- When profiling production applications (CPU, memory, async)
- When correlating logs across services via trace context
- When debugging production issues with structured logs

## Core Concepts

### Three Pillars of Observability

| Pillar | Purpose | Tool | Data Type |
|--------|---------|------|-----------|
| **Logs** | Discrete events with context | structlog, ELK, Loki | Text/JSON |
| **Metrics** | Aggregated numeric time series | Prometheus, Grafana | Counters, gauges, histograms |
| **Traces** | Request lifecycle across services | OpenTelemetry, Jaeger, Tempo | Spans with context |

### SLO / SLI / Error Budgets

| Term | Definition | Example |
|------|-----------|---------|
| **SLI** (Service Level Indicator) | Quantitative measure of reliability | `successful_requests / total_requests` |
| **SLO** (Service Level Objective) | Target value for SLI | `99.9% successful requests` |
| **Error Budget** | Acceptable failure window | `0.1% = 43.2 min/month` |

```
Error Budget (monthly) = (1 - SLO) × minutes_in_month
99.9%  → 43.2 min/month
99.95% → 21.6 min/month
99.99% →  4.3 min/month
```

### Observability vs Monitoring

- **Monitoring** — known unknowns: dashboards and alerts for things you anticipated
- **Observability** — unknown unknowns: ability to debug novel issues using logs, metrics, and traces together
- **Goal**: given any alert, trace it from metric → trace → log line → root cause in < 15 minutes

---

## Patterns

### 1. Structured Logging (structlog)

```python
import logging
import structlog
from structlog.types import Processor

# Production configuration — JSON output for log aggregation (Loki, ELK, CloudWatch)
def configure_logging(
    *,
    json_output: bool = True,
    min_level: int = logging.INFO,
    service_name: str = "myapp",
) -> None:
    """Configure structlog for production or development."""

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,   # Inject trace context
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # Production — JSON for log aggregation
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development — colored console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Standard library integration
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(min_level)

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


logger = structlog.get_logger()

# ✅ GOOD: Bind context — every log line includes these fields
async def process_order(order_id: int, user_id: int):
    log = logger.bind(order_id=order_id, user_id=user_id)
    log.info("order_processing_started")

    try:
        order = await fetch_order(order_id)
        log.info("order_fetched", status=order.status, total=float(order.total))

        await charge_payment(order)
        log.info("payment_charged", amount=float(order.total))

        await fulfill_order(order)
        log.info("order_fulfilled", tracking_number=order.tracking)

    except PaymentError as exc:
        log.error("payment_failed", error=str(exc), retry_count=exc.retry_count)
        raise
    except Exception:
        log.exception("order_processing_unexpected_error")  # Includes stack trace
        raise
```

**FastAPI request logging middleware:**

```python
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request context to all loggers in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        log = logger.bind(request_id=request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            log.info(
                "http_request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
            return response

        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "http_request_failed",
                duration_ms=round(duration_ms, 2),
            )
            raise
```

---

### 2. Distributed Tracing (OpenTelemetry)

```python
# observability/tracing.py — OpenTelemetry setup
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

def setup_tracing(
    service_name: str,
    service_version: str,
    otlp_endpoint: str = "http://localhost:4317",
    sample_rate: float = 1.0,  # 1.0 = trace everything; 0.1 = 10%
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing with OTLP exporter."""

    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": "production",
    })

    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sample_rate),
    )

    # Export spans to OTLP collector (Jaeger, Tempo, etc.)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            schedule_delay_millis=5000,   # Flush every 5 seconds
            max_export_batch_size=512,
        )
    )

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


# Auto-instrument frameworks and libraries
def instrument_app(app, engine):
    """Auto-instrument FastAPI, SQLAlchemy, and HTTPX."""
    FastAPIInstrumentor.instrument_app(app)          # HTTP spans
    SQLAlchemyInstrumentor().instrument(engine=engine) # DB query spans
    HTTPXClientInstrumentor().instrument()             # Outbound HTTP spans


# ✅ GOOD: Manual spans for business logic
tracer = trace.get_tracer("order-service")

async def process_order(order_id: int):
    with tracer.start_as_current_span(
        "process_order",
        attributes={"order.id": order_id},
    ) as span:
        try:
            order = await fetch_order(order_id)
            span.set_attribute("order.status", order.status)
            span.set_attribute("order.total", float(order.total))

            with tracer.start_as_current_span("charge_payment") as payment_span:
                result = await charge_payment(order)
                payment_span.set_attribute("payment.txn_id", result.txn_id)

            with tracer.start_as_current_span("fulfill_order"):
                await fulfill_order(order)

            span.set_status(StatusCode.OK)

        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
```

**Context propagation (cross-service):**

```python
# OpenTelemetry automatically propagates trace context via W3C Trace Context headers
# traceparent: 00-<trace_id>-<span_id>-<flags>
# tracestate: vendor-specific data

# With HTTPX — context is auto-propagated by HTTPXClientInstrumentor
import httpx

async def call_downstream_service(url: str):
    async with httpx.AsyncClient() as client:
        # W3C traceparent header is auto-injected
        response = await client.get(url)
    return response.json()

# With aiohttp / requests — use propagator manually
from opentelemetry.propagate import inject

async def call_with_aiohttp(url: str):
    headers = {}
    inject(headers)  # Injects traceparent into headers dict
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers=headers)
    return await response.json()
```

---

### 3. Metrics Collection (Prometheus)

```python
# observability/metrics.py — Prometheus metrics
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response

# Counters — monotonically increasing (requests, errors, events)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

order_events = Counter(
    "order_events_total",
    "Total order lifecycle events",
    ["event_type"],  # created, paid, shipped, cancelled
)

# Gauges — current value (can go up and down)
active_connections = Gauge(
    "active_connections",
    "Number of active WebSocket connections",
)

db_pool_available = Gauge(
    "db_pool_available_connections",
    "Available database connections in pool",
)

queue_depth = Gauge(
    "task_queue_depth",
    "Number of pending tasks in queue",
    ["queue_name"],
)

# Histograms — distribution of values (latency, size)
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

response_size = Histogram(
    "http_response_size_bytes",
    "HTTP response body size",
    buckets=[100, 1000, 10000, 100000, 1000000],
)

# Info — static metadata
app_info = Info(
    "app",
    "Application metadata",
)
app_info.info({"version": "1.2.3", "commit": "abc123"})


# FastAPI middleware for automatic HTTP metrics
class PrometheusMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        start = time.perf_counter()

        status_code = 500
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            http_requests_total.labels(
                method=method, endpoint=path, status_code=str(status_code)
            ).inc()
            http_request_duration.labels(
                method=method, endpoint=path
            ).observe(duration)


# Metrics endpoint for Prometheus scraping
@router.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

---

### 4. Health Checks

```python
# observability/health.py — Kubernetes-compatible health probes
from enum import Enum
from pydantic import BaseModel
from fastapi import HTTPException

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ComponentHealth(BaseModel):
    status: HealthStatus
    latency_ms: float | None = None
    details: dict | None = None

class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    components: dict[str, ComponentHealth]


class HealthChecker:
    """Aggregates health from multiple components."""

    def __init__(self):
        self._checks: dict[str, callable] = {}

    def register(self, name: str, check_fn: callable):
        self._checks[name] = check_fn

    async def check_all(self) -> HealthResponse:
        """Run all health checks — used for /health/readiness."""
        components = {}
        overall = HealthStatus.HEALTHY

        for name, check_fn in self._checks.items():
            try:
                start = time.perf_counter()
                result = await check_fn()
                latency = (time.perf_counter() - start) * 1000

                if result:
                    components[name] = ComponentHealth(
                        status=HealthStatus.HEALTHY,
                        latency_ms=round(latency, 2),
                    )
                else:
                    components[name] = ComponentHealth(
                        status=HealthStatus.UNHEALTHY,
                        latency_ms=round(latency, 2),
                    )
                    overall = HealthStatus.UNHEALTHY
            except Exception as exc:
                components[name] = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    details={"error": str(exc)},
                )
                overall = HealthStatus.UNHEALTHY

        return HealthResponse(
            status=overall,
            version=settings.APP_VERSION,
            components=components,
        )


# Individual check functions
async def check_database() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    try:
        return await redis_client.ping()
    except Exception:
        return False

async def check_downstream_api() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.DOWNSTREAM_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


# Register checks
health_checker = HealthChecker()
health_checker.register("database", check_database)
health_checker.register("redis", check_redis)
health_checker.register("downstream_api", check_downstream_api)


# Kubernetes probe endpoints
@router.get("/health/live")
async def liveness():
    """Liveness probe — is the process alive?
    Returns 200 if the app is running. Kubernetes restarts on failure.
    Keep this simple — don't check dependencies.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe — can the app serve traffic?
    Returns 200 only if all dependencies are healthy.
    Kubernetes removes from Service endpoints on failure.
    """
    result = await health_checker.check_all()
    if result.status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result


@router.get("/health/startup")
async def startup():
    """Startup probe — has the app finished initializing?
    Used for slow-starting containers.
    Kubernetes waits before enabling liveness/readiness.
    """
    if not app.state.initialized:
        raise HTTPException(status_code=503, detail="Still starting")
    return {"status": "ready"}
```

---

### 5. SLO / SLI Implementation

```python
# observability/slo.py — SLO monitoring with Prometheus
from prometheus_client import Counter, Histogram

# SLI: Success rate — (successful requests) / (total requests)
http_requests = Counter(
    "slo_http_requests_total",
    "Total requests for SLO calculation",
    ["service", "status_class"],  # status_class: 2xx, 3xx, 4xx, 5xx
)

# SLI: Latency — percentage of requests under threshold
http_latency = Histogram(
    "slo_http_request_duration_seconds",
    "Request duration for SLO latency calculation",
    ["service", "endpoint"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

# Record SLI data
def record_request(service: str, status_code: int, duration: float):
    """Record a request for SLO tracking."""
    status_class = f"{status_code // 100}xx"
    http_requests.labels(service=service, status_class=status_class).inc()
    http_latency.labels(service=service, endpoint="all").observe(duration)


# PromQL queries for SLO dashboards:
#
# Availability SLI (last 5 min):
#   sum(rate(slo_http_requests_total{status_class=~"2xx|3xx"}[5m]))
#   /
#   sum(rate(slo_http_requests_total[5m]))
#
# Latency SLI (p99 < 500ms, last 5 min):
#   histogram_quantile(0.99,
#     sum(rate(slo_http_request_duration_seconds_bucket[5m])) by (le)
#   )
#
# Error Budget remaining:
#   1 - (
#     sum(rate(slo_http_requests_total{status_class="5xx"}[30d]))
#     /
#     sum(rate(slo_http_requests_total[30d]))
#   ) / (1 - 0.999)  -- SLO target = 99.9%


class SLOMonitor:
    """Track error budget consumption in real-time."""

    def __init__(self, slo_target: float = 0.999, window_days: int = 30):
        self.slo_target = slo_target
        self.window_days = window_days
        self.error_budget = 1.0 - slo_target  # 0.001 for 99.9%

    def check_budget(self, error_rate: float) -> dict:
        """Check if error budget is being consumed too fast."""
        budget_remaining = self.error_budget - error_rate
        budget_percent = budget_remaining / self.error_budget * 100

        return {
            "slo_target": f"{self.slo_target * 100}%",
            "error_rate": f"{error_rate * 100:.4f}%",
            "budget_remaining": f"{budget_percent:.1f}%",
            "status": self._budget_status(budget_percent),
        }

    def _budget_status(self, remaining_pct: float) -> str:
        if remaining_pct > 50:
            return "healthy"       # More than half budget left
        elif remaining_pct > 20:
            return "caution"       # Budget depleting — slow down deploys
        elif remaining_pct > 0:
            return "danger"        # Freeze non-critical deploys
        else:
            return "exhausted"     # Budget exceeded — halt deploys, fix reliability
```

---

### 6. Alerting Patterns

```python
# Alerting philosophy: alert on SYMPTOMS, not causes
#
# ✅ Symptom-based (good alerts):
#   - "Error rate > 0.1% for 5 minutes" — users are hurting
#   - "p99 latency > 1s for 5 minutes" — users are waiting
#   - "Error budget exhausted" — reliability degraded
#
# ❌ Cause-based (bad alerts):
#   - "CPU > 80%" — maybe it's fine, maybe it's not
#   - "Disk > 90%" — depends on growth rate
#   - "Connection pool at 80%" — may never cause user impact

# Prometheus alerting rules (YAML for Alertmanager)
ALERTING_RULES = """
groups:
  - name: slo_alerts
    rules:
      # Symptom: users are getting errors
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate exceeds SLO (0.1%)"
          runbook: "https://wiki.example.com/runbooks/high-error-rate"

      # Symptom: users are waiting too long
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p99 latency exceeds 1 second"

      # Symptom: error budget nearly exhausted
      - alert: ErrorBudgetBurn
        expr: |
          (
            sum(rate(http_requests_total{status_code=~"5.."}[1h]))
            / sum(rate(http_requests_total[1h]))
          ) > (14.4 * 0.001)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error budget burning 14.4x faster than sustainable"
"""

# Multi-window burn rate alerting (Google SRE approach)
#
# | Window | Burn Rate | Severity | Action            |
# |--------|-----------|----------|-------------------|
# | 1h     | 14.4x     | critical | Page on-call      |
# | 6h     | 6x        | critical | Page during hours |
# | 1d     | 3x        | warning  | Ticket to team    |
# | 3d     | 1x        | info     | Review in standup |
#
# Burn rate = (current error rate) / (error budget rate)
# 14.4x burn rate = entire monthly budget consumed in ~50 hours
```

---

### 7. Profiling (py-spy, memray, async-debug)

```python
# CPU profiling with py-spy (sampling profiler — safe for production)
# Install: pip install py-spy
#
# Usage:
#   py-spy top --pid $(pgrep -f "uvicorn myapp")     # Live top-N functions
#   py-spy record -o profile.svg --pid <PID>          # Flame graph
#   py-spy dump --pid <PID>                            # Stack dump (like jstack)

# Memory profiling with memray
# Install: pip install memray
#
# Usage:
#   memray run --trace-python-allocators app.py       # Full allocation tracking
#   memray flamegraph memray-results.bin               # Generate flame graph
#   memray summary memray-results.bin                  # Top allocation sites
#   memray table memray-results.bin                    # Allocation table

# In-process memory snapshot
import tracemalloc

async def memory_snapshot_endpoint():
    """Endpoint to capture memory snapshot in production."""
    if not tracemalloc.is_tracing():
        tracemalloc.start(25)  # Keep 25 frames per allocation
        return {"status": "tracing started, call again for snapshot"}

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("traceback")

    top_allocations = []
    for stat in top_stats[:20]:
        top_allocations.append({
            "file": str(stat.traceback),
            "size_kb": stat.size / 1024,
            "count": stat.count,
        })

    return {
        "total_traced_kb": sum(s.size for s in top_stats) / 1024,
        "top_allocations": top_allocations,
    }


# Async debugging — detect blocked event loop
import asyncio

async def detect_event_loop_blocking():
    """Enable slow callback detection — logs when event loop is blocked."""
    loop = asyncio.get_running_loop()
    loop.slow_callback_duration = 0.1  # Warn if callback takes > 100ms

    # Enable debug mode (dev only — adds significant overhead)
    # loop.set_debug(True)


# FastAPI endpoint for runtime profiling
@router.get("/debug/asyncio")
async def asyncio_debug_info():
    """Expose event loop health metrics."""
    loop = asyncio.get_running_loop()
    return {
        "running": loop.is_running(),
        "closed": loop.is_closed(),
        "slow_callback_duration": loop.slow_callback_duration,
    }
```

---

### 8. Log Correlation (trace_id in logs)

```python
# Connect logs → traces → metrics for full request visibility
import structlog
from opentelemetry import trace

class TraceContextProcessor:
    """Inject OpenTelemetry trace context into every log line."""

    def __call__(self, logger, method_name, event_dict):
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
            event_dict["trace_flags"] = format(ctx.trace_flags, "02x")
        return event_dict


# Configure structlog with trace context injection
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        TraceContextProcessor(),            # Inject trace_id, span_id
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

# Result — every log line includes trace context:
# {
#   "event": "order_created",
#   "level": "info",
#   "timestamp": "2026-07-24T10:30:00Z",
#   "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
#   "span_id": "00f067aa0ba902b7",
#   "order_id": 12345,
#   "user_id": 678
# }

# Loki/Grafana: click trace_id → jump to Jaeger/Tempo trace view
# Jaeger: click span → see correlated log lines for that span


# ✅ GOOD: Structured error with full context
async def handle_payment(order_id: int, amount: Decimal):
    log = logger.bind(order_id=order_id, amount=float(amount))
    try:
        result = await payment_gateway.charge(amount)
        log.info("payment_processed",
                 txn_id=result.txn_id,
                 gateway=result.gateway)
        return result
    except PaymentDeclined as exc:
        log.warning("payment_declined",
                    reason=exc.reason,
                    gateway_code=exc.code)
        raise
    except PaymentGatewayTimeout:
        log.error("payment_gateway_timeout",
                  timeout_ms=5000,
                  gateway="stripe")
        raise
```

---

## Best Practices

1. **Log at boundaries** — log at function entry/exit, not inside loops
2. **Structured over unstructured** — use `logger.bind(key=value)` not f-strings
3. **Trace everything** — propagate `trace_id` across service boundaries (W3C Trace Context)
4. **Metrics for aggregates, logs for details** — use metrics for dashboards, logs for debugging
5. **Set histogram buckets deliberately** — default Prometheus buckets rarely match your latency profile
6. **Health checks must be fast** — timeout at 5 seconds, don't check deep dependencies in liveness
7. **Alert on symptoms, not causes** — "error rate high" not "CPU high"
8. **Include runbook links in alerts** — every alert should link to remediation steps
9. **Sample traces in production** — trace 1-10% of requests, not 100% (overhead)
10. **Correlate everything** — `request_id` in HTTP headers, `trace_id` in logs, `span_id` in traces
11. **Use `perf_counter()` for durations** — `time.time()` is affected by clock adjustments
12. **Suppress noisy loggers** — set third-party libraries to WARNING level
13. **Rotate and ship logs** — use sidecar or DaemonSet to ship JSON logs to aggregation (Loki, ELK)
14. **Monitor the monitoring** — alert if metrics endpoint stops responding or scrape fails

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `logger.info(f"User {user_id} did {action}")` | Unstructured — can't query by field | `logger.bind(user_id=..., action=...).info("user_action")` |
| Logging sensitive data (PII, tokens) | Compliance violation, security risk | Redact fields, use `structlog` processors to filter |
| 100% trace sampling in production | CPU overhead, storage cost | `TraceIdRatioBased(0.01)` — sample 1% |
| Health check queries heavy SQL | Slows down the app it's checking | Use `SELECT 1` or lightweight ping |
| Alerting on CPU/memory | False positives, not user-impacting | Alert on error rate and latency (symptoms) |
| No `trace_id` in logs | Can't correlate logs to traces | Inject via OpenTelemetry context processor |
| Default histogram buckets | p99 always falls in last bucket | Set custom buckets matching your SLO |
| `time.time()` for durations | Affected by NTP adjustments | Use `time.perf_counter()` |
| Logging inside tight loops | Gigabytes of logs, performance impact | Log at loop boundaries or sample every Nth iteration |
| Missing error labels on metrics | Can't distinguish error types in PromQL | Label with `error_type` or `exception_class` |
| No runbook for alerts | On-call spends 30 min figuring out what to do | Link runbook URL in alert annotation |
| Synchronous logging in async code | Blocks event loop | Use async-capable logging or offload to thread |

---

## Context7 Integration

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| OpenTelemetry | `/websites/opentelemetry_io` | Tracing setup, instrumentation, propagation |
| structlog | `/hynek/structlog` | Configuration, processors |
| Prometheus | `/prometheus/client_python` | Client instrumentation |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.

**When to query:**
- Before setting up OpenTelemetry — verify current SDK version and auto-instrumentation packages
- When configuring structlog processors — check for new built-in processors
- When defining Prometheus metrics — verify current client API and best practices
- When implementing health probes — check Kubernetes probe configuration guidelines
