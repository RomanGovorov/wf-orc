# Advanced Patterns: CI/CD Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Advanced GitHub Actions Patterns

### Database Migration Drift Check

```yaml
# Alembic migration check in CI
migration-check:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:17
      env:
        POSTGRES_DB: migration_test
        POSTGRES_PASSWORD: testpass
      ports: ['5432:5432']
  env:
    DATABASE_URL: postgresql://postgres:testpass@localhost:5432/migration_test
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v6
      with: { python-version: '3.12' }
    - run: pip install -e ".[dev]"

    # Apply all migrations FIRST — autogenerate must diff the models against
    # the MIGRATED schema, not an empty database
    - name: Run migrations
      run: alembic upgrade head

    # Drift check: a fresh autogenerate against the migrated schema must be empty
    - name: Check autogenerate produces no changes
      run: |
        alembic revision --autogenerate -m "ci-drift-check" --rev-id ci_drift_check
        drift_file=$(find alembic/versions -name '*ci_drift_check*')
        if grep -qE '^[[:space:]]*op\.' "$drift_file"; then
          echo "ERROR: Uncommitted migration detected — models changed without a migration."
          echo "Run 'alembic revision --autogenerate' locally and commit the result."
          rm -f "$drift_file"
          exit 1
        fi
        rm -f "$drift_file"

    # Test downgrade (optional)
    - name: Test downgrade
      run: alembic downgrade -1
```

### Pinning Image Tag at Deploy Time

```yaml
# Deploy job step — the workflow run expands ${{ github.sha }}
# GitOps variant: commit the updated kustomization.yaml and let ArgoCD sync it
- name: Pin image tag and deploy
  run: |
    cd k8s/production
    kustomize edit set image ghcr.io/org/myapp:${{ github.sha }}
    kustomize build . | kubectl apply -f -
```

### Pipeline Monitoring & Deployment Health

```yaml
# CI/CD pipeline metrics
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

## Advanced Docker Patterns

### Layer Caching Optimization

```dockerfile
# ✅ GOOD — maximize layer caching
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy only requirements first — cached unless they change
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Copy application code — rebuilds only when code changes
COPY . .
RUN python -m compileall .
```

### Security Hardening

```dockerfile
FROM python:3.12-slim AS production

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Remove unnecessary packages
RUN apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

# Read-only filesystem mounts
VOLUME ["/tmp", "/var/log"]

# Drop all capabilities
RUN apt-get update && apt-get install -y libcap2-bin \
    && setcap cap_net_bind_service=+ep /usr/local/bin/python \
    && apt-get purge -y --auto-remove libcap2-bin

USER appuser

# Prevent privilege escalation
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

### Multi-Platform Builds

```yaml
# GitHub Actions — build for multiple architectures
- uses: docker/build-push-action@v6
  with:
    push: true
    platforms: linux/amd64,linux/arm64
    tags: |
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Advanced Kubernetes Patterns

### Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

### Resource Quotas and Limits

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: myapp-quota
  namespace: myapp
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: myapp-limits
  namespace: myapp
spec:
  limits:
    - default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      type: Container
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: myapp-network-policy
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: database
      ports:
        - protocol: TCP
          port: 5432
```

## Advanced Terraform Patterns

### Module Composition

```hcl
# modules/ecs-service/main.tf
module "ecs_service" {
  source = "./modules/ecs-service"
  
  app_name        = var.app_name
  environment     = var.environment
  image_tag       = var.image_tag
  desired_count   = var.desired_count
  
  # Networking
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  public_subnets  = module.vpc.public_subnet_ids
  
  # Database
  database_url    = module.rds.connection_string
  
  # Monitoring
  log_group_name  = module.logging.log_group_name
}
```

### State Management

```hcl
terraform {
  backend "s3" {
    bucket         = "myapp-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "myapp-terraform-locks"  # For Terraform < 1.10
    # use_lockfile = true  # For Terraform >= 1.10 (S3-native locking)
  }
}
```

### Workspaces for Environments

```hcl
# Use workspaces for environment-specific state
resource "aws_ecs_cluster" "this" {
  name = "${var.app_name}-${terraform.workspace}"
  
  tags = {
    Environment = terraform.workspace
  }
}

# Variable files per workspace
# terraform.tfvars           # default
# production.tfvars          # terraform workspace select production
# staging.tfvars             # terraform workspace select staging
```

## Advanced GitOps Patterns

### Automated Sync with Health Checks

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # Ignore HPA-managed replicas
```

### Image Updater (Automated Image Updates)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  annotations:
    argocd-image-updater.argoproj.io/image.update-list: "myapp"
    argocd-image-updater.argoproj.io/myapp.allow-tags: "regexp:^[0-9a-f]{7,40}$"
spec:
  # ArgoCD Image Updater automatically updates image tags
```

## Edge Cases

### Handling Secrets in CI

```yaml
# GitHub Actions — use secrets
steps:
  - name: Deploy
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      API_KEY: ${{ secrets.API_KEY }}
    run: |
      # Secrets are automatically masked in logs
      echo "Deploying with secure credentials"

# GitLab CI — use CI/CD variables
deploy:
  script:
    - echo "Deploying with $DATABASE_URL"
    # Variables marked as "masked" in CI/CD settings
```

### Rollback Strategies

```bash
# Kubernetes rollback
kubectl rollout undo deployment/myapp -n production
kubectl rollout undo deployment/myapp --to-revision=3

# Terraform rollback
terraform state pull > backup.tfstate
terraform apply -target=module.problematic_module

# Docker rollback
docker service update --rollback myapp
```

### Handling Flaky Tests

```yaml
# Retry flaky tests
- name: Run tests with retry
  uses: nick-fields/retry@v3
  with:
    timeout_minutes: 5
    max_attempts: 3
    command: pytest tests/ -k "not slow"
  
# Quarantine flaky tests
- name: Run stable tests
  run: pytest tests/ --ignore=tests/flaky/

- name: Run flaky tests (allowed to fail)
  continue-on-error: true
  run: pytest tests/flaky/
```

## Performance Considerations

### Pipeline Caching

```yaml
# GitHub Actions — cache dependencies
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      .venv
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

# Docker — BuildKit cache
- uses: docker/build-push-action@v6
  with:
    cache-from: type=registry,ref=ghcr.io/org/myapp:buildcache
    cache-to: type=registry,ref=ghcr.io/org/myapp:buildcache,mode=max
```

### Parallel Jobs

```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/unit/

  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
    steps:
      - run: pytest tests/integration/

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/e2e/

  # All test jobs run in parallel
  deploy:
    needs: [test-unit, test-integration, test-e2e]
    runs-on: ubuntu-latest
    steps:
      - run: echo "All tests passed, deploying"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Pipeline slow | Sequential jobs, no caching | Parallelize, add caching |
| Docker build fails | Missing dependencies, wrong order | Multi-stage, copy requirements first |
| Terraform drift | Manual changes | Import resources, enforce IaC |
| Deployment fails health check | Wrong probe path, timeout | Check health endpoint, increase timeout |
| Secrets exposed | Not masked in CI | Use secret managers, mask variables |
| Rollback fails | No previous revision | Keep revision history, use blue-green |
| Image pull fails | Wrong tag, auth issue | Use SHA tags, verify credentials |
| HPA not scaling | Missing metrics, wrong thresholds | Check metrics server, adjust thresholds |

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
