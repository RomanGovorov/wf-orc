---
name: ci-cd-patterns
description: CI/CD Patterns — pipeline design, deployment strategy, Docker best practices, IaC, GitOps, monitoring. Use when setting up CI/CD, containerization, deployment, IaC.
priority: 5
paths:
  - "Dockerfile*"
  - "docker-compose*"
  - ".github/workflows/**"
  - ".gitlab-ci*"
  - "Jenkinsfile*"
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/terraform/**"
  - "**/kubernetes/**"
  - "**/k8s/**"
  - "**/helm/**"
  - "**/ansible/**"
  - "**/deployment-manifest*"
  - "**/kubernetes/**/*.yml"
---

# CI/CD Patterns

Template for setting up CI/CD pipelines — from lint and tests to production deployment. Includes Docker multi-stage builds, deployment strategies, Infrastructure as Code patterns, and GitOps.

## When to Use This Skill

- When setting up a CI/CD pipeline (GitHub Actions, GitLab CI)
- When creating Dockerfiles for containerization
- When configuring deployment strategy (blue-green, canary, rolling)
- When writing Infrastructure as Code (Terraform)
- When setting up GitOps workflows
- When configuring monitoring and alerting

## Core Concepts

### 1. Pipeline Stages

```
┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌───────────┐
│ Lint │ -> │ Test │ -> │Build │ -> │Deploy│ -> │  Monitor  │
│      │    │      │    │      │    │(staging)│   │(production)│
└──────┘    └──────┘    └──────┘    └──────┘    └───────────┘
```

- **Lint**: Code style, type checking, static analysis — fail fast
- **Test**: Unit, integration, E2E — quality gate
- **Build**: Create artifacts (Docker image, binary)
- **Deploy**: Automatic to staging, manual to production
- **Monitor**: Health checks, smoke tests, alerting

### 2. Deployment Strategies

| Strategy | Downtime | Risk | Rollback |
|---|---|---|---|
| Recreate | Yes | High | Slow |
| Rolling | No | Medium | Slow |
| Blue-Green | No | Low | Fast |
| Canary | No | Very Low | Fast |

### 3. Infrastructure as Code

- **Immutability** — infrastructure is immutable, not mutable
- **Idempotency** — running N times = one result
- **Version control** — all changes via PR

## Patterns

### Pattern 1: CI Pipeline — GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install ruff mypy
      - run: ruff check . --output-format=github
      - run: ruff format . --check
      - run: mypy myapp/ --ignore-missing-imports

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
        run: |
          pytest tests/ --cov=myapp --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v5
        with:
          files: ./coverage.xml
          token: ${{ secrets.CODECV_TOKEN }}

  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v4
      - uses: docker/login-action@v4
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Pattern 2: Docker Multi-Stage Build

```dockerfile
# Build stage — build/test tools + pre-compiled wheels
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt requirements-build.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
RUN pip install --no-cache-dir -r requirements-build.txt

COPY . .
RUN python -m compileall .

# Final stage — minimal runtime
FROM python:3.12-slim AS production

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /wheels /wheels
COPY --from=builder requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels requirements.txt
COPY --from=builder --chown=appuser:appuser /app /app

WORKDIR /app

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

USER appuser
EXPOSE 8000

CMD ["gunicorn", "myapp.main:app", \
     "-w", "4", "-k", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

### Pattern 3: Terraform — AWS Infrastructure

```hcl
# main.tf — ECS Fargate deployment
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  required_version = ">= 1.10"

  backend "s3" {
    bucket = "myapp-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
    use_lockfile = true
  }
}

resource "aws_ecs_cluster" "this" {
  name = "${var.app_name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = var.app_name
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_ssm_parameter.db_url.arn },
      { name = "SECRET_KEY", valueFrom = aws_ssm_parameter.secret_key.arn }
    ]
  }])
}

resource "aws_ecs_service" "this" {
  name            = "${var.app_name}-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
```

### Pattern 4: Kubernetes Deployment with HPA

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: ghcr.io/org/myapp:stable
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Pattern 5: GitOps — ArgoCD

```yaml
# argocd-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/myapp-infra
    targetRevision: main
    path: k8s/production
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Pattern 6: Canary Deployment

```yaml
# argo-rollouts — canary strategy
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 25
        - pause: {duration: 10m}
        - setWeight: 50
        - pause: {duration: 15m}
        - setWeight: 75
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 100
      analysis:
        templates:
          - templateName: error-rate
```

### Pattern 7: Security Scanning

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Semgrep
        run: pipx install semgrep && semgrep ci
      - name: Run Bandit
        run: pip install bandit && bandit -r src/ -f json -o bandit-report.json
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2

  container-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - name: Build image to scan
        run: docker build -t app:${{ github.sha }} .
      - uses: aquasecurity/trivy-action@v0.29.0
        with:
          image-ref: app:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

## Best Practices

1. **Pipeline must be fast** — <10 min from commit to deploy
2. **Fail fast** — lint → unit → integration → e2e
3. **Immutable artifacts** — Docker image with git SHA tag
4. **No secrets in CI logs** — masked variables, vault integration
5. **Automated deployment** — no manual server access
6. **One-click rollback** — or automatic rollback
7. **Zero downtime** — rolling updates or blue-green
8. **Infrastructure as Code** — never change manually
9. **Health checks** — liveness + readiness probes
10. **Monitor everything** — metrics, logs, traces

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Secrets in CI logs | Exposed credentials | Mask variables, vault, secret managers |
| Monolithic pipeline | All stages sequential, slow | Parallel independent jobs |
| No rollback plan | Broke prod — no way back | Blue-green, canary, automated rollback |
| Mutable infrastructure | Drift, snowflake servers | IaC (Terraform), immutable |
| No health checks | Unhealthy pods receive traffic | Liveness + readiness probes |
| Deploy on every commit | Wasted resources | Commit batching, staging auto, prod manual |
| Single build target | No caching | Multi-stage, layer caching |
| Missing monitoring | Don't know what broke | Metrics, logs, alerts, tracing |

## Context7 Integration

When Context7 MCP tools are available, use them to fetch up-to-date library documentation.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| GitHub Actions | `/websites/github_en_actions` | Workflow syntax, actions |
| Docker | `/docker/docs` | Multi-stage builds, best practices |
| Terraform | `/websites/developer_hashicorp_terraform` | Provider config, modules |
| Kubernetes | `/kubernetes/website` | Deployment manifests, HPA |
| ArgoCD | `/argoproj/argo-cd` | GitOps configuration |

> **See also**: `observability-patterns` — Application-level Prometheus metrics, SLO monitoring.

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates
