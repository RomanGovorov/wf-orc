---
name: ci-cd-patterns
description: CI/CD Patterns — pipeline design, deployment strategies, Docker best practices, IaC, GitOps, monitoring. Use when setting up CI/CD, containerization, deployment, IaC.
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

### Pattern 1: CI Pipeline — GitHub Actions (FastAPI)

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
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy

      - name: Ruff check
        run: ruff check . --output-format=github

      - name: Ruff format check
        run: ruff format . --check

      - name: MyPy type check
        run: mypy myapp/ --ignore-missing-imports

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
        run: |
          pytest tests/ \
            --cov=myapp \
            --cov-report=xml \
            --cov-fail-under=80 \
            --junitxml=junit.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: junit.xml

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

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

### Pattern 2: Docker Multi-Stage Build

```dockerfile
# Build stage — compile/test dependencies
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt requirements-build.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements-build.txt

# Copy application code
COPY . .
# Pre-compile Python files — faster startup
RUN python -m compileall .

# Final stage — minimal runtime
FROM python:3.12-slim AS production

# Non-root user — security best practice
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install only runtime dependencies
COPY --from=builder /install /usr/local
COPY --from=builder --chown=appuser:appuser /app /app

WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run as non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run with gunicorn — production server
CMD ["gunicorn", "myapp.main:app", \
     "-w", "4", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Pattern 3: Terraform — AWS Infrastructure (FastAPI)

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"

  backend "s3" {
    bucket = "myapp-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS cluster
resource "aws_ecs_cluster" "this" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS task definition
resource "aws_ecs_task_definition" "this" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = var.app_name
      image     = "${var.ecr_repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      environment = [
        { name = "APP_ENV", value = var.environment }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_ssm_parameter.db_url.arn
        },
        {
          name      = "SECRET_KEY"
          valueFrom = aws_ssm_parameter.secret_key.arn
        }
      ]
    }
  ])
}

# Application Load Balancer
resource "aws_lb" "this" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "this" {
  name        = "${var.app_name}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }
}

# ECS Service with rolling deployment
resource "aws_ecs_service" "this" {
  name            = "${var.app_name}-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = var.app_name
    container_port   = 8000
  }

  deployment_controller {
    type = "ECS"  # Rolling updates
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.this]
}
```

### Pattern 4: GitOps — ArgoCD

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
      - PrunePropagationPolicy=foreground
  # Health check
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

### Pattern 5: Kubernetes Deployment (with HPA)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    app: myapp
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
          image: ghcr.io/org/myapp:${{ github.sha }}  # Use SHA-based tags, never :latest in production
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
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
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
        - setWeight: 10       # 10% traffic to new
        - pause: {duration: 5m}
        - setWeight: 25       # 25% traffic
        - pause: {duration: 10m}
        - setWeight: 50       # 50% traffic
        - pause: {duration: 15m}
        - setWeight: 75       # 75% traffic
        - pause: {duration: 10m}
        # Auto-analysis before 100%
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 100      # Full rollout
      # Auto-rollback if analysis fails
      analysis:
        templates:
          - templateName: error-rate
          - templateName: latency-p95
```

### Pattern 7: Pipeline Monitoring & Deployment Health

```yaml
# CI/CD pipeline metrics (GitHub Actions example)
- name: Pipeline duration tracking
  run: |
    echo "PIPELINE_DURATION=$SECONDS" >> "$GITHUB_ENV"

# Deployment health checks
- name: Post-deploy health check
  run: |
    for i in $(seq 1 10); do
      status=$(curl -sf "$HEALTH_URL/health" -o /dev/null -w '%{http_code}')
      [ "$status" = "200" ] && echo "Healthy" && exit 0
      sleep 5
    done
    echo "Health check failed" && exit 1

# Rollback trigger on failure
- name: Automatic rollback
  if: failure()
  run: |
    kubectl rollout undo deployment/$APP_NAME -n $NAMESPACE
    echo "Rolled back to previous revision"
```

**Key pipeline metrics:**
- Build duration and trend
- Deployment frequency
- Change failure rate
- Mean time to recovery (MTTR)
- Test execution time breakdown

> **See also**: `observability-patterns` — Application-level Prometheus metrics, custom histograms, SLO monitoring.

### Node.js CI Pipeline (GitHub Actions)
```yaml
name: Node.js CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [20, 22]
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_PASSWORD: testpass
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-node${{ matrix.node-version }}
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: app:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### SAST/DAST Security Scanning
```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Semgrep — static analysis
      - name: Run Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/python
            p/owasp-top-ten
            p/security-audit
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_TOKEN }}

      # Bandit — Python-specific security linter
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install bandit
      - run: bandit -r src/ -f json -o bandit-report.json

      # Secret scanning
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  container-scan:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: aquasecurity/trivy-action@v0.29.0
        with:
          image-ref: app:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

### Database Migration in CI
```yaml
# Alembic migration check in CI
  migration-check:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: migration_test
          POSTGRES_PASSWORD: testpass
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -e ".[dev]"

      # Check for uncommitted migrations
      - name: Check autogenerate produces no changes
        run: |
          alembic revision --autogenerate -m "check"
          if [ -n "$(git status --porcelain alembic/versions/)" ]; then
            echo "ERROR: Uncommitted migration detected. Run 'alembic revision --autogenerate' locally."
            exit 1
          fi

      # Run all migrations
      - name: Run migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/migration_test

      # Test downgrade (optional — verify rollback works)
      - name: Test downgrade
        run: alembic downgrade -1
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/migration_test
```

### GitLab CI Pipeline
```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  POSTGRES_DB: testdb
  POSTGRES_USER: testuser
  POSTGRES_PASSWORD: testpass
  POSTGRES_HOST: postgres
  POSTGRES_PORT: 5432

lint:
  stage: lint
  image: python:3.12-slim
  script:
    - pip install ruff mypy
    - ruff check src/
    - mypy src/

test:
  stage: test
  image: python:3.12-slim
  services:
    - postgres:16-alpine
  script:
    - pip install -e ".[dev]"
    - alembic upgrade head
    - pytest --cov=src --cov-report=xml
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  coverage: '/TOTAL.*\s+(\d+%)$/'

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
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

When working with CI/CD patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| GitHub Actions | `/websites/github_en_actions` | Workflow syntax, actions |
| Docker | `/docker/docs` | Multi-stage builds, best practices |
| Terraform | `/websites/developer_hashicorp_terraform` | Provider config, modules |
| Kubernetes | `/kubernetes/website` | Deployment manifests, HPA |
| ArgoCD | `/argoproj/argo-cd` | GitOps configuration |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.
