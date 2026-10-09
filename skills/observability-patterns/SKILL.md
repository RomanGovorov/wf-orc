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

def configure_logging(*, json_output: bool = True, min_level: int = logging.INFO):
    """Configure structlog for production or development."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    renderer = (
        structlog.processors.JSONRenderer() if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(min_level)

logger = structlog.get_logger()

# ✅ GOOD: Bind context — every log line includes these fields
async def process_order(order_id: int, user_id: int):
    log = logger.bind(order_id=order_id, user_id=user_id)
    log.info("order_processing_started")
    
    try:
        order = await fetch_order(order_id)
        log.info("order_fetched", status=order.status)
        await charge_payment(order)
        log.info("payment_charged", amount=float(order.total))
    except PaymentError as exc:
        log.error("payment_failed", error=str(exc))
        raise
```

**FastAPI request logging middleware:**

```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        
        log = logger.bind(request_id=request_id)
        start = time.perf_counter()
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            log.info("http_request_completed", status_code=response.status_code, duration_ms=round(duration_ms, 2))
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            log.exception("http_request_failed")
            raise
```

### 2. Distributed Tracing (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

def setup_tracing(service_name: str, otlp_endpoint: str, sample_rate: float = 1.0):
    """Initialize OpenTelemetry tracing with OTLP exporter."""
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment.name": "production",
    })
    
    provider = TracerProvider(resource=resource, sampler=TraceIdRatioBased(sample_rate))
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter, max_queue_size=2048))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

# Auto-instrument frameworks
def instrument_app(app, engine):
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()

# Manual spans for business logic
tracer = trace.get_tracer("order-service")

async def process_order(order_id: int):
    with tracer.start_as_current_span("process_order", attributes={"order.id": order_id}) as span:
        try:
            order = await fetch_order(order_id)
            span.set_attribute("order.status", order.status)
            
            with tracer.start_as_current_span("charge_payment"):
                await charge_payment(order)
            
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
```

### 3. Metrics Collection (Prometheus)

```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Counters — monotonically increasing
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

# Gauges — current value (can go up and down)
active_connections = Gauge("active_connections", "Number of active connections")

# Histograms — distribution of values
http_request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# FastAPI middleware for automatic metrics
class PrometheusMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope["method"]
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
            route = scope.get("route")
            endpoint = getattr(route, "path_format", None) or "unmatched"
            http_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
            http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 4. Health Checks

```python
from enum import Enum
from pydantic import BaseModel

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ComponentHealth(BaseModel):
    status: HealthStatus
    latency_ms: float | None = None

class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    components: dict[str, ComponentHealth]

class HealthChecker:
    def __init__(self):
        self._checks: dict[str, tuple[CheckFn, bool]] = {}

    def register(self, name: str, check_fn: CheckFn, *, critical: bool = True):
        self._checks[name] = (check_fn, critical)

    async def check_all(self) -> HealthResponse:
        components = {}
        overall = HealthStatus.HEALTHY
        
        for name, (check_fn, critical) in self._checks.items():
            try:
                start = time.perf_counter()
                ok = bool(await check_fn())
                latency = round((time.perf_counter() - start) * 1000, 2)
            except Exception:
                ok = False
                latency = None
            
            components[name] = ComponentHealth(
                status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
                latency_ms=latency,
            )
            
            if not ok:
                if critical:
                    overall = HealthStatus.UNHEALTHY
                elif overall is HealthStatus.HEALTHY:
                    overall = HealthStatus.DEGRADED
        
        return HealthResponse(status=overall, version=settings.APP_VERSION, components=components)

# Kubernetes probe endpoints
@router.get("/health/live")
async def liveness():
    """Liveness probe — is the process alive?"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness():
    """Readiness probe — can the app serve traffic?"""
    result = await health_checker.check_all()
    if result.status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result
```

### 5. Log Correlation (trace_id in logs)

```python
from opentelemetry import trace

class TraceContextProcessor:
    """Inject OpenTelemetry trace context into every log line."""
    def __call__(self, logger, method_name, event_dict):
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
        return event_dict

# Configure structlog with trace context injection
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        TraceContextProcessor(),
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

# Result — every log line includes trace context:
# {"event": "order_created", "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", ...}
```

### 6. Alerting Patterns

```python
# Alert on SYMPTOMS, not causes
# ✅ Symptom-based (good): "Error rate > 0.1% for 5 minutes"
# ❌ Cause-based (bad): "CPU > 80%"

# Prometheus alerting rules (YAML for Alertmanager)
ALERTING_RULES = """
groups:
  - name: slo_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate exceeds SLO (0.1%)"
          runbook: "https://wiki.example.com/runbooks/high-error-rate"
      
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
"""
```

## Best Practices

1. **Log at boundaries** — log at function entry/exit, not inside loops
2. **Structured over unstructured** — use `logger.bind(key=value)` not f-strings
3. **Trace everything** — propagate `trace_id` across service boundaries
4. **Metrics for aggregates, logs for details** — metrics for dashboards, logs for debugging
5. **Set histogram buckets deliberately** — default buckets rarely match your latency profile
6. **Health checks must be fast** — timeout at 5 seconds, don't check deep dependencies in liveness
7. **Alert on symptoms, not causes** — "error rate high" not "CPU high"
8. **Include runbook links in alerts** — every alert should link to remediation steps
9. **Sample traces in production** — trace 1-10% of requests, not 100%
10. **Correlate everything** — `request_id` in HTTP headers, `trace_id` in logs
11. **Use `perf_counter()` for durations** — `time.time()` is affected by clock adjustments
12. **Suppress noisy loggers** — set third-party libraries to WARNING level

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `logger.info(f"User {user_id}")` | Unstructured — can't query | `logger.bind(user_id=...).info("user_action")` |
| Logging sensitive data | Compliance violation | Redact fields, use processors to filter |
| 100% trace sampling | CPU overhead, storage cost | `TraceIdRatioBased(0.01)` — sample 1% |
| Health check queries heavy SQL | Slows down the app | Use `SELECT 1` or lightweight ping |
| Alerting on CPU/memory | False positives | Alert on error rate and latency |
| No `trace_id` in logs | Can't correlate | Inject via OpenTelemetry context processor |
| Default histogram buckets | p99 in last bucket | Set custom buckets matching SLO |
| `time.time()` for durations | Affected by NTP | Use `time.perf_counter()` |
| Logging inside tight loops | Gigabytes of logs | Log at boundaries or sample every Nth |
| No runbook for alerts | On-call confusion | Link runbook URL in alert annotation |

## Context7 Integration

When Context7 MCP tools are available, use them to fetch up-to-date library documentation.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| OpenTelemetry | `/websites/opentelemetry_io` | Tracing setup, instrumentation |
| structlog | `/hynek/structlog` | Configuration, processors |
| Prometheus | `/prometheus/client_python` | Client instrumentation |

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates
