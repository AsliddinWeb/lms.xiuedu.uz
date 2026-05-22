# 07.03. Monitoring va Observability

## Maqsad

Tizimning sog'lomligini, performance'ini va xatolarni real vaqtda kuzatib borish.

## Stack

| Komponent | Texnologiya | Vazifa |
|-----------|-------------|--------|
| Metrics | Prometheus | Vaqt qatori metrikalar |
| Visualization | Grafana | Dashboard'lar |
| Logs | Loki + Promtail | Log aggregation |
| Tracing | Jaeger / Tempo | Distributed tracing |
| Errors | Sentry | Xato tracking |
| Uptime | Uptime Kuma | Servis mavjudligi |
| Alerts | Alertmanager + Telegram | Ogohlantirishlar |

## Arxitektura

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Backend  │  │ Frontend │  │  Celery  │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │              │
     │ /metrics    │ Sentry       │ /metrics
     ▼             ▼              ▼
┌──────────────────────────────────────┐
│         Prometheus (scrape)          │
└─────────────────┬────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │    Grafana     │◄────── Loki (logs)
         └────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ Alertmanager   │──► Telegram
         └────────────────┘
```

## Prometheus konfiguratsiyasi

`infra/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'backend'
    metrics_path: /metrics
    static_configs:
      - targets: ['backend:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

## FastAPI metrics

`app/core/monitoring.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Request, Response
from time import time

# Metrikalar
http_requests_total = Counter(
    "http_requests_total",
    "Jami HTTP so'rovlar",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP so'rov davomiyligi",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_users = Gauge(
    "active_users",
    "Hozirda faol foydalanuvchilar"
)

db_connections = Gauge(
    "db_connections_active",
    "Faol DB ulanishlari"
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Jami Celery vazifalar",
    ["task_name", "status"]
)

# Middleware
async def metrics_middleware(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    duration = time() - start_time

    endpoint = request.url.path
    method = request.method
    status = response.status_code

    http_requests_total.labels(method, endpoint, status).inc()
    http_request_duration_seconds.labels(method, endpoint).observe(duration)

    return response

# Endpoint
async def metrics_endpoint():
    return Response(content=generate_latest(), media_type="text/plain")

def setup_monitoring(app: FastAPI):
    app.middleware("http")(metrics_middleware)
    app.get("/metrics")(metrics_endpoint)
```

## Sentry sozlash

`app/core/sentry.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

def init_sentry(dsn: str, environment: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,  # 10% so'rovlarni trace qilamiz
        profiles_sample_rate=0.1,
        send_default_pii=False,  # PII ma'lumotlarni yubormaslik
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        before_send=filter_sensitive_data,
    )

def filter_sensitive_data(event, hint):
    """Sensitive ma'lumotlarni Sentry'ga yubormaslik."""
    if "request" in event and "data" in event["request"]:
        sensitive_fields = ["password", "token", "passport_pinfl", "card_number"]
        for field in sensitive_fields:
            if field in event["request"]["data"]:
                event["request"]["data"][field] = "[FILTERED]"
    return event
```

`app/main.py`:

```python
from app.core.sentry import init_sentry
from app.core.monitoring import setup_monitoring
from app.core.config import settings

if settings.SENTRY_DSN:
    init_sentry(settings.SENTRY_DSN, settings.ENVIRONMENT)

app = FastAPI(title="LMS API")
setup_monitoring(app)
```

## Frontend monitoring

`frontend/src/main.ts`:

```typescript
import * as Sentry from "@sentry/vue"

Sentry.init({
  app,
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration({ router }),
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.05,
  replaysOnErrorSampleRate: 1.0,
})
```

## Grafana Dashboardlar

### 1. System Overview

Asosiy metrikalar:
- HTTP RPS (so'rovlar/soniya)
- Latency (p50, p95, p99)
- Error rate (%)
- Active users
- DB connection pool
- Redis hit rate

### 2. Business Metrics

- Faol talabalar soni
- Tugallangan kurslar
- Imtihon natijalari
- To'lov tranzaksiyalari
- Yangi ro'yxatdan o'tishlar

### 3. Infrastructure

- CPU, RAM, Disk usage
- Network I/O
- Container resource consumption

## Alert Rules

`infra/prometheus/rules/alerts.yml`:

```yaml
groups:
  - name: lms_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (endpoint)
           / sum(rate(http_requests_total[5m])) by (endpoint)) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Yuqori xatolik foizi: {{ $labels.endpoint }}"
          description: "{{ $labels.endpoint }} uchun xatolik foizi 5%dan oshib ketdi"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Yuqori javob vaqti"
          description: "P95 latency 2 soniyadan oshdi"

      # Database
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL ishlamayapti"

      - alert: HighDBConnections
        expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DB ulanishlari 80%dan oshdi"

      # Redis
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical

      # Disk space
      - alert: DiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk bo'sh joy 15%dan kam"

      # Memory
      - alert: HighMemoryUsage
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
           / node_memory_MemTotal_bytes > 0.9
        for: 10m
        labels:
          severity: warning

      # SSL certificate
      - alert: SSLCertExpiringSoon
        expr: probe_ssl_earliest_cert_expiry - time() < 7 * 24 * 3600
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL sertifikat 7 kun ichida tugaydi"
```

## Alertmanager + Telegram

`infra/alertmanager/config.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'telegram'
  routes:
    - match:
        severity: critical
      receiver: 'telegram-critical'

receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1001234567890
        parse_mode: 'HTML'
        message: |
          <b>{{ .Status | toUpper }}</b>: {{ .GroupLabels.alertname }}
          {{ range .Alerts }}
          <b>Severity:</b> {{ .Labels.severity }}
          <b>Summary:</b> {{ .Annotations.summary }}
          <b>Description:</b> {{ .Annotations.description }}
          {{ end }}

  - name: 'telegram-critical'
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: -1009876543210  # Critical alerts uchun alohida chat
```

## Logging strategiya

### Structured logging

`app/core/logging.py`:

```python
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()

    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level'}
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Misol foydalanish
logger = logging.getLogger(__name__)
logger.info("User logged in", extra={
    "user_id": str(user.id),
    "ip_address": request.client.host,
    "user_agent": request.headers.get("user-agent"),
})
```

## Loki konfiguratsiyasi

`infra/loki/loki-config.yml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 720h  # 30 kun
```

## Acceptance kriteriyalar

- [ ] Prometheus barcha servislardan metrikalar yig'adi
- [ ] Grafana dashboardlari sozlangan
- [ ] Sentry orqali xatolar yig'iladi
- [ ] Alert qoidalari ishlaydi
- [ ] Telegram'ga ogohlantirishlar yetib boradi
- [ ] Log retention 30 kun
- [ ] SSL muddati monitoring qilinadi
- [ ] Backup status monitoring qilinadi
- [ ] Uptime ≥ 99.5%
