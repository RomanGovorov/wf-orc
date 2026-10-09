# Advanced Patterns: Observability Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Advanced OpenTelemetry Patterns

### Context Propagation (Cross-Service)

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
import aiohttp
from opentelemetry.propagate import inject

async def call_with_aiohttp(url: str):
    headers = {}
    inject(headers)  # Injects traceparent into headers dict
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers=headers)
    return await response.json()
```

### Custom Span Attributes and Events

```python
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer(__name__)

async def process_payment(order_id: int, amount: Decimal):
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("payment.amount", float(amount))
        span.set_attribute("payment.currency", "USD")
        
        # Add events for important milestones
        span.add_event("payment_validation_started")
        await validate_payment_method(order_id)
        span.add_event("payment_validation_completed")
        
        try:
            result = await charge_payment_gateway(amount)
            span.set_attribute("payment.transaction_id", result.txn_id)
            span.add_event("payment_charged", attributes={"gateway": result.gateway})
            span.set_status(StatusCode.OK)
            return result
        except PaymentDeclined as exc:
            span.set_attribute("payment.decline_reason", exc.reason)
            span.set_attribute("payment.gateway_code", exc.code)
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
```

### Sampling Strategies

```python
from opentelemetry.sdk.trace.sampling import (
    TraceIdRatioBased,
    ParentBased,
    ALWAYS_ON,
    ALWAYS_OFF,
)

# Parent-based sampling: follow parent's decision, default to 10% for root spans
sampler = ParentBased(
    root=TraceIdRatioBased(0.1),  # 10% of root spans
)

# Advanced: sample based on attributes (requires custom sampler)
class SmartSampler:
    """Sample all errors and 1% of successful requests."""
    
    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        # Always sample if error is expected
        if attributes and attributes.get("sampling.priority") == "high":
            return ALWAYS_ON.should_sample(parent_context, trace_id, name, kind, attributes, links)
        # Otherwise sample 1%
        return TraceIdRatioBased(0.01).should_sample(parent_context, trace_id, name, kind, attributes, links)
```

## Advanced Prometheus Patterns

### Cardinality Management

```python
# ⚠️ CARDINALITY: never label with the raw request path
# /users/1, /users/2, ... each create a NEW time series

# ❌ BAD — unbounded cardinality
http_requests_total.labels(method="GET", endpoint="/users/123", status="200").inc()

# ✅ GOOD — bounded cardinality (route template)
http_requests_total.labels(method="GET", endpoint="/users/{user_id}", status="200").inc()

# Extract route template from Starlette scope
route = scope.get("route")
endpoint = getattr(route, "path_format", None) or "unmatched"
```

### Custom Metrics for Business Logic

```python
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
order_events = Counter(
    "order_events_total",
    "Total order lifecycle events",
    ["event_type"],  # created, paid, shipped, cancelled
)

payment_gateway_latency = Histogram(
    "payment_gateway_duration_seconds",
    "Payment gateway response time",
    ["gateway", "status"],  # stripe|adyen, success|declined|timeout
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

active_subscriptions = Gauge(
    "active_subscriptions",
    "Number of active subscriptions",
    ["plan_type"],  # basic|pro|enterprise
)

# Usage
async def create_order(user_id: int, items: list[dict]):
    order = await db.create_order(user_id, items)
    order_events.labels(event_type="created").inc()
    
    try:
        await charge_payment(order)
        order_events.labels(event_type="paid").inc()
    except PaymentDeclined:
        order_events.labels(event_type="cancelled").inc()
        raise
```

### Histogram Bucket Tuning

```python
# Default Prometheus buckets: [.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
# These rarely match your actual latency profile

# For API endpoints (typical web app)
api_latency_buckets = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# For database queries (faster)
db_query_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]

# For external API calls (slower)
external_api_buckets = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]

# Define buckets based on your SLO
# If SLO is p99 < 500ms, ensure buckets cover 0.5s with granularity
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.0, 5.0],
)
```

## Advanced Health Check Patterns

### Deep Health Checks with Dependency Details

```python
async def check_database() -> tuple[bool, dict]:
    """Check database with detailed diagnostics."""
    try:
        start = time.perf_counter()
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            latency = round((time.perf_counter() - start) * 1000, 2)
            
            # Check connection pool stats
            pool_stats = {
                "pool_size": session.bind.pool.size(),
                "checked_in": session.bind.pool.checkedin(),
                "checked_out": session.bind.pool.checkedout(),
            }
            
            return True, {"latency_ms": latency, "pool": pool_stats}
    except Exception as exc:
        return False, {"error": str(exc), "type": type(exc).__name__}

async def check_redis() -> tuple[bool, dict]:
    """Check Redis with memory and connection info."""
    try:
        info = await redis_client.info()
        return True, {
            "connected_clients": info["connected_clients"],
            "used_memory_human": info["used_memory_human"],
            "uptime_seconds": info["uptime_in_seconds"],
        }
    except Exception as exc:
        return False, {"error": str(exc)}
```

### Circuit Breaker for Health Checks

```python
from circuitbreaker import circuit

@circuit(fail_max=3, reset_timeout=60)
async def check_downstream_api() -> bool:
    """Check downstream API with circuit breaker."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.DOWNSTREAM_URL}/health")
        return resp.status_code == 200

# After 3 failures, circuit opens and returns False immediately for 60 seconds
# Prevents cascading failures when dependency is down
```

## Advanced SLO/SLI Implementation

### Multi-Window Burn Rate Alerting

```python
# Google SRE approach: alert on burn rate over multiple windows
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

PROMQL_BURN_RATE = """
# 1-hour burn rate (last 5 minutes)
(
  sum(rate(http_requests_total{status_code=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m]))
) / (1 - 0.999)  # SLO target = 99.9%

# Alert if burn rate > 14.4 for 5 minutes
"""

class MultiWindowBurnRateAlert:
    def __init__(self, slo_target: float = 0.999):
        self.slo_target = slo_target
        self.error_budget = 1.0 - slo_target
        
        # Burn rate thresholds
        self.thresholds = {
            "1h": 14.4,
            "6h": 6.0,
            "1d": 3.0,
            "3d": 1.0,
        }
    
    def calculate_burn_rate(self, error_rate: float, window_hours: int) -> float:
        """Calculate burn rate over a time window."""
        # Error budget consumption rate per hour
        budget_rate_per_hour = self.error_budget / (30 * 24)  # 30-day month
        current_rate_per_hour = error_rate
        
        return current_rate_per_hour / budget_rate_per_hour
```

### SLI Dashboards (PromQL)

```python
# PromQL queries for SLO dashboards

# Availability SLI (last 5 min)
AVAILABILITY_SLI = """
sum(rate(http_requests_total{status_class=~"2xx|3xx"}[5m]))
/
sum(rate(http_requests_total[5m]))
"""

# Latency SLI (p99 < 500ms, last 5 min)
LATENCY_SLI = """
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)
"""

# Error Budget remaining (30-day window)
ERROR_BUDGET_REMAINING = """
1 - (
  sum(rate(http_requests_total{status_class="5xx"}[30d]))
  /
  sum(rate(http_requests_total[30d]))
) / (1 - 0.999)  # SLO target = 99.9%
"""
```

## Advanced Profiling Patterns

### Memory Profiling with memray

```python
import memray

# Profile memory allocations
with memray.Tracker("output.bin"):
    # Code to profile
    data = load_large_dataset()
    result = process_data(data)

# Analyze results
# memray flamegraph output.bin -o flamegraph.html
```

### CPU Profiling with py-spy

```bash
# Attach to running process
py-spy record -o profile.svg --pid 12345

# Sample for 60 seconds
py-spy record -d 60 -o profile.svg --pid 12345

# Top-like view
py-spy top --pid 12345
```

### Async Profiling

```python
import asyncio
import time

class AsyncProfiler:
    """Profile async code with proper event loop awareness."""
    
    def __init__(self):
        self.spans = []
    
    async def trace(self, name: str):
        """Async context manager for profiling."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.spans.append({"name": name, "duration": duration})

# Usage
async def process_request():
    profiler = AsyncProfiler()
    
    async with profiler.trace("fetch_user"):
        user = await fetch_user(user_id)
    
    async with profiler.trace("fetch_orders"):
        orders = await fetch_orders(user_id)
    
    print(profiler.spans)
```

## Edge Cases

### Log Redaction (PII/Sensitive Data)

```python
import structlog

def redact_sensitive_fields(logger, method_name, event_dict):
    """Redact sensitive fields from logs."""
    sensitive_keys = {"password", "token", "secret", "api_key", "ssn", "credit_card"}
    
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    
    return event_dict

structlog.configure(
    processors=[
        redact_sensitive_fields,
        structlog.processors.JSONRenderer(),
    ],
)
```

### Structured Error Logging with Full Context

```python
from decimal import Decimal

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

### Metrics Endpoint Security

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_metrics_access(credentials: HTTPBasicCredentials = Depends(security)):
    """Protect /metrics endpoint with basic auth."""
    if not hmac.compare_digest(
        credentials.username.encode(), settings.METRICS_USERNAME.encode()
    ) or not hmac.compare_digest(
        credentials.password.encode(), settings.METRICS_PASSWORD.encode()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@router.get("/metrics", dependencies=[Depends(verify_metrics_access)])
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Performance Considerations

### Async Logging

```python
# Synchronous logging in async code blocks the event loop
# Use async-capable logging or offload to thread

import logging
from concurrent.futures import ThreadPoolExecutor

class AsyncLogHandler(logging.Handler):
    """Offload log writes to thread pool."""
    
    def __init__(self, target_handler):
        super().__init__()
        self.target = target_handler
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def emit(self, record):
        self.executor.submit(self.target.emit, record)

# Usage
file_handler = logging.FileHandler("app.log")
async_handler = AsyncLogHandler(file_handler)
logger.addHandler(async_handler)
```

### Log Aggregation at Scale

```python
# For high-throughput apps, batch logs before shipping
import structlog
from structlog.stdlib import ProcessorFormatter

# Use QueueHandler for async log processing
from logging.handlers import QueueHandler, QueueListener
import queue

log_queue = queue.Queue(maxsize=10000)
queue_handler = QueueHandler(log_queue)

# Listener processes logs in separate thread
listener = QueueListener(log_queue, file_handler, stream_handler)
listener.start()

# All loggers use queue handler
root_logger.addHandler(queue_handler)
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Missing trace context in logs | Processor not configured | Add `TraceContextProcessor` to structlog |
| High cardinality metrics | Raw path in labels | Use route template (`/users/{id}`) |
| Health check timeouts | Checking heavy dependencies | Use lightweight checks (`SELECT 1`) |
| Logs not appearing | Handler not flushed | Call `handler.flush()` or use async logging |
| Trace spans not exported | Exporter misconfigured | Check OTLP endpoint and network |
| Metrics endpoint slow | Too many metrics | Reduce metric count, check cardinality |
| Error budget calculation wrong | Wrong time window | Use 30-day rolling window in PromQL |

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
