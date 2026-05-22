# 02. Texnologik Stek (Tech Stack)

## Backend

### Asosiy tillar va frameworklar

```toml
[python]
version = ">=3.11"
package_manager = "uv"  # yoki poetry, lekin uv tezroq

[backend]
fastapi = ">=0.110"
uvicorn = "^0.29"           # ASGI server
pydantic = "^2.6"
pydantic-settings = "^2.2"  # Sozlamalar

[orm]
sqlalchemy = "^2.0"         # Async support
alembic = "^1.13"           # Migratsiyalar
asyncpg = "^0.29"           # PostgreSQL async driver

[auth]
python-jose = "^3.3"        # JWT
passlib = "^1.7"            # Parol hash
bcrypt = "^4.1"
pyotp = "^2.9"              # 2FA TOTP

[task-queue]
celery = "^5.3"
redis = "^5.0"
flower = "^2.0"             # Celery monitoring

[testing]
pytest = "^8.0"
pytest-asyncio = "^0.23"
httpx = "^0.27"
testcontainers = "^4.0"
faker = "^24.0"

[code-quality]
ruff = "^0.3"               # Linter (replaces flake8 + isort)
mypy = "^1.9"               # Type checker
black = "^24.0"             # Formatter

[utilities]
httpx = "^0.27"             # HTTP klient
celery-beat = "^2.6"        # Scheduled tasks
python-multipart = "^0.0.9" # Form data
email-validator = "^2.1"
phonenumbers = "^8.13"
qrcode = "^7.4"
reportlab = "^4.1"          # PDF
weasyprint = "^61.0"        # HTML → PDF

[ai-ml-proctoring]
opencv-python = "^4.9"      # Computer vision
face-recognition = "^1.3"   # Face detection
mediapipe = "^0.10"         # Eye tracking
openai-whisper = "^20231117" # Audio transkripsiya

[observability]
opentelemetry-api = "^1.23"
opentelemetry-instrumentation-fastapi = "^0.44b0"
prometheus-fastapi-instrumentator = "^7.0"
structlog = "^24.1"         # Structured logging
sentry-sdk = "^1.40"
```

### `pyproject.toml` namuna

```toml
[project]
name = "lms-backend"
version = "0.1.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "B", "UP", "ASYNC"]
```

## Frontend

### Asosiy stek

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "@vueuse/core": "^10.9.0",
    "axios": "^1.6.0",
    "tailwindcss": "^3.4.0",
    "@headlessui/vue": "^1.7.0",
    "@heroicons/vue": "^2.1.0",
    "lucide-vue-next": "^0.350.0",
    "vue-i18n": "^9.10.0",
    "vee-validate": "^4.12.0",
    "yup": "^1.3.0",
    "date-fns": "^3.3.0",
    "chart.js": "^4.4.0",
    "vue-chartjs": "^5.3.0",
    "video.js": "^8.10.0",
    "@vimeo/player": "^2.20.0",
    "hls.js": "^1.5.0",
    "tiptap": "^2.2.0",
    "socket.io-client": "^4.7.0",
    "vue-toastification": "^2.0.0-rc.5"
  },
  "devDependencies": {
    "vite": "^5.1.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.4.0",
    "vue-tsc": "^2.0.0",
    "@types/node": "^20.11.0",
    "vitest": "^1.3.0",
    "@vue/test-utils": "^2.4.0",
    "playwright": "^1.42.0",
    "eslint": "^8.57.0",
    "eslint-plugin-vue": "^9.22.0",
    "@typescript-eslint/parser": "^7.1.0",
    "prettier": "^3.2.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### UI komponentlar
- **shadcn-vue** yoki **PrimeVue** — komponentlar
- **Headless UI** — accessible primitives
- **Tailwind CSS** — utility-first styling

## Maʼlumotlar bazasi

### PostgreSQL 15+
- Asosiy MB
- Async driver: `asyncpg`
- Connection pool: `pgbouncer`
- Backup: `pgBackRest`

### Redis 7+
- Sessiyalar
- Kesh (kontent metadatasi)
- Celery broker
- Rate limiting
- Pub/Sub (real-time notif)

### OpenSearch (yoki Elasticsearch)
- Full-text search
- Logs aggregation (alternativ)

### MinIO
- Object storage
- S3-compatible API
- Video, hujjatlar, profilerasm

## Infratuzilma

### Containerization
```yaml
# Texnologiyalar
docker: "24+"
docker-compose: "v2.24+"
kubernetes: "1.29+"
helm: "3.14+"
```

### Reverse Proxy
- **Nginx** (production)
- **Traefik** (Kubernetes uchun, ixtiyoriy)
- **Caddy** (dev uchun)

### CI/CD
- **GitLab CI** yoki **GitHub Actions**
- **Argo CD** (K8s GitOps)
- **Trivy** (image scanning)

### Monitoring
- **Prometheus** — metrikalar
- **Grafana** — dashboard
- **Loki** — loglar (yoki ELK)
- **Jaeger / Tempo** — distributed tracing
- **Alertmanager** — alertlar
- **Sentry** — frontend errors
- **UptimeRobot** — external monitoring

## Tashqi xizmatlar

### Live Video
- **Zoom** (Server-to-Server OAuth)
- **BigBlueButton** (alternativ, self-hosted)
- **Jitsi Meet** (yengil alternativ)

### To'lov
- **Click** API
- **Payme** Subscribe API
- **Apelsin**
- **Stripe** (xorijiy talabalar uchun, ixtiyoriy)

### Identity
- **OneID** (Yagona Identifikatsiya)
- **HEMIS SSO**
- **Google OAuth** (xorijiy uchun)

### Communications
- **Eskiz.uz** — SMS
- **PlayMobile** — backup SMS
- **SMTP (mahalliy)** + **SendGrid** (backup) — email
- **Telegram Bot API** — bot xabarnoma

### Plagiat
- **Antiplag.uz** — mahalliy
- **Turnitin** — xalqaro (ixtiyoriy)

### AI/ML (avtoproktoring)
- Open-source: OpenCV + face_recognition + Whisper
- Yoki tashqi: **Examus**, **ProctorEdu** (commercial)

## Versiyalar

### Production minimum versiyalar

```
Python:        3.11.8+
Node.js:       20.11.0+ (LTS)
PostgreSQL:    15.6+
Redis:         7.2.4+
Docker:        24.0+
Kubernetes:    1.29+
Nginx:         1.25+
```

## Sabablari (Why this stack?)

### Nega FastAPI?
- Async/await native
- Avtomatik OpenAPI/Swagger
- Pydantic validation
- Type hints
- Yuqori unumdorlik (Starlette + uvicorn)

### Nega Vue 3?
- Composition API + TypeScript
- Engil va tez
- Pinia state management
- Yaxshi ekosistema
- Past kirish chegarasi (jamoa uchun)

### Nega PostgreSQL?
- ACID, ishonchli
- JSONB (yarim-strukturlangan)
- Full-text search
- Materialized views
- Yuqori darajadagi extensiyalar (pg_trgm, postgis)

### Nega Tailwind?
- Utility-first
- Bundle size kichik (purge)
- Custom design tez
- Komponentsiz, moslashuvchan

### Nega Docker + K8s?
- Standardizatsiya
- Auto-scaling
- Self-healing
- GitOps deployment
- Portativlik
