# Code Examples: Observability Patterns

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete FastAPI Application with Observability

### Application Setup

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from observability.logging import configure_logging, logger
from observability.tracing import setup_tracing, instrument_app
from observability.metrics import PrometheusMiddleware
from observability.health import health_checker, check_database, check_redis
from app.core.db import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging(json_output=True, min_level=logging.INFO)
    setup_tracing(service_name="myapp", otlp_endpoint="http://localhost:4317")
    
    # Register health checks
    health_checker.register("database", check_database)
    health_checker.register("redis", check_redis)
    
    logger.info("application_started", version=settings.APP_VERSION)
    yield
    # Shutdown
    await engine.dispose()
    logger.info("application_shutdown")

app = FastAPI(title="MyApp", lifespan=lifespan)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMiddleware)

# Auto-instrument for tracing
instrument_app(app, engine)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(observability_router)  # /health, /metrics
```

### Observability Router

```python
# observability/router.py
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

observability_router = APIRouter(tags=["observability"])

@observability_router.get("/health/live")
async def liveness():
    return {"status": "alive"}

@observability_router.get("/health/ready")
async def readiness():
    result = await health_checker.check_all()
    if result.status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result

@observability_router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Example 2: Complete Structured Logging Setup

### Configuration

```python
# observability/logging.py
import logging
import structlog
from structlog.types import Processor

def configure_logging(
    *,
    json_output: bool = True,
    min_level: int = logging.INFO,
    service_name: str = "myapp",
) -> None:
    """Configure structlog for production or development."""
    
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
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
```

### Request Logging Middleware

```python
# observability/middleware.py
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

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

### Usage in Endpoints

```python
# app/api/endpoints/orders.py
from observability.logging import logger

@router.post("/orders")
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    log = logger.bind(user_id=data.user_id)
    log.info("order_creation_started", items_count=len(data.items))
    
    try:
        order = await OrderService(db).create(data)
        log.info(
            "order_created",
            order_id=order.id,
            total=float(order.total),
        )
        return order
    except InsufficientStock as exc:
        log.warning(
            "order_creation_failed",
            error="insufficient_stock",
            product_id=exc.product_id,
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        log.exception("order_creation_unexpected_error")
        raise
```

## Example 3: Complete OpenTelemetry Setup

### Tracing Configuration

```python
# observability/tracing.py
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
    sample_rate: float = 0.1,  # 10% sampling
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing with OTLP exporter."""
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment.name": "production",
    })

    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sample_rate),
    )

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            schedule_delay_millis=5000,
            max_export_batch_size=512,
        )
    )

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

def instrument_app(app, engine):
    """Auto-instrument FastAPI, SQLAlchemy, and HTTPX."""
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
```

### Manual Spans

```python
# app/services/payment_service.py
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer("payment-service")

class PaymentService:
    async def process_payment(self, order_id: int, amount: Decimal):
        with tracer.start_as_current_span(
            "process_payment",
            attributes={"order.id": order_id, "payment.amount": float(amount)},
        ) as span:
            try:
                # Validate
                with tracer.start_as_current_span("validate_payment"):
                    await self.validate_payment_method(order_id)
                
                # Charge
                with tracer.start_as_current_span("charge_gateway") as charge_span:
                    result = await self.charge_gateway(amount)
                    charge_span.set_attribute("payment.txn_id", result.txn_id)
                    charge_span.set_attribute("payment.gateway", result.gateway)
                
                # Record
                with tracer.start_as_current_span("record_transaction"):
                    await self.record_transaction(order_id, result)
                
                span.set_status(StatusCode.OK)
                return result
                
            except PaymentDeclined as exc:
                span.set_attribute("payment.decline_reason", exc.reason)
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
```

## Example 4: Complete Prometheus Metrics

### Metrics Definition

```python
# observability/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Info

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Application metrics
active_connections = Gauge(
    "active_connections",
    "Number of active WebSocket connections",
)

db_pool_available = Gauge(
    "db_pool_available_connections",
    "Available database connections in pool",
)

# Business metrics
order_events = Counter(
    "order_events_total",
    "Total order lifecycle events",
    ["event_type"],
)

payment_gateway_latency = Histogram(
    "payment_gateway_duration_seconds",
    "Payment gateway response time",
    ["gateway", "status"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

# App info
app_info = Info("app", "Application metadata")
app_info.info({"version": "1.2.3", "commit": "abc123"})
```

### Metrics Middleware

```python
# observability/middleware.py
import time

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
            
            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()
            http_request_duration.labels(
                method=method, endpoint=endpoint
            ).observe(duration)
```

## Example 5: Complete Health Check System

### Health Checker

```python
# observability/health.py
import time
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

CheckFn = Callable[[], Awaitable[bool]]

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
                details = None
            except Exception as exc:
                ok = False
                latency = None
                details = {"error": str(exc)}

            components[name] = ComponentHealth(
                status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
                latency_ms=latency,
                details=details,
            )

            if not ok:
                if critical:
                    overall = HealthStatus.UNHEALTHY
                elif overall is HealthStatus.HEALTHY:
                    overall = HealthStatus.DEGRADED

        return HealthResponse(
            status=overall,
            version=settings.APP_VERSION,
            components=components,
        )

# Individual checks
async def check_database() -> bool:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return True

async def check_redis() -> bool:
    return await redis_client.ping()

async def check_downstream_api() -> bool:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.DOWNSTREAM_URL}/health")
        return resp.status_code == 200

# Register
health_checker = HealthChecker()
health_checker.register("database", check_database)
health_checker.register("redis", check_redis)
health_checker.register("downstream_api", check_downstream_api, critical=False)
```

## Example 6: Complete SLO Monitoring

### SLO Implementation

```python
# observability/slo.py
from prometheus_client import Counter, Histogram

# SLI metrics
http_requests = Counter(
    "slo_http_requests_total",
    "Total requests for SLO calculation",
    ["service", "status_class"],
)

http_latency = Histogram(
    "slo_http_request_duration_seconds",
    "Request duration for SLO latency calculation",
    ["service", "endpoint"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

def record_request(service: str, status_code: int, duration: float):
    """Record a request for SLO tracking."""
    status_class = f"{status_code // 100}xx"
    http_requests.labels(service=service, status_class=status_class).inc()
    http_latency.labels(service=service, endpoint="all").observe(duration)

class SLOMonitor:
    def __init__(self, slo_target: float = 0.999, window_days: int = 30):
        self.slo_target = slo_target
        self.window_days = window_days
        self.error_budget = 1.0 - slo_target

    def check_budget(self, error_rate: float) -> dict:
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
            return "healthy"
        elif remaining_pct > 20:
            return "caution"
        elif remaining_pct > 0:
            return "danger"
        else:
            return "exhausted"

# Usage
slo_monitor = SLOMonitor(slo_target=0.999)

@router.get("/slo/status")
async def get_slo_status():
    # Calculate error rate from Prometheus
    error_rate = await calculate_error_rate()  # Implement with PromQL
    return slo_monitor.check_budget(error_rate)
```

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
