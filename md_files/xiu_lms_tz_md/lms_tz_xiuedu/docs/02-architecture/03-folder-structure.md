# 03. Loyiha Papka Tuzilmasi (Folder Structure)

## Monorepo strukturasi

```
oliy-lms/
├── README.md
├── docker-compose.yml              # Dev muhit
├── docker-compose.prod.yml         # Production
├── .gitignore
├── .gitlab-ci.yml                  # yoki .github/workflows/
├── docs/                           # Bu loyiha hujjatlari
│
├── backend/                        # FastAPI ilovasi
├── frontend/                       # Vue 3 SPA
├── infra/                          # Infrastructure as Code
└── scripts/                        # Yordamchi skriptlar
```

## Backend tuzilmasi

```
backend/
├── pyproject.toml
├── poetry.lock                     # yoki uv.lock
├── Dockerfile
├── .env.example
├── alembic.ini
├── pytest.ini
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   │
│   ├── core/                       # Asosiy konfiguratsiya
│   │   ├── __init__.py
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── security.py             # JWT, hashing
│   │   ├── database.py             # DB engine + session
│   │   ├── redis.py                # Redis client
│   │   ├── celery_app.py           # Celery instance
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── middleware.py           # Middlewares
│   │   ├── deps.py                 # Common dependencies
│   │   └── logging.py              # Structured logging
│   │
│   ├── api/                        # HTTP API endpoints
│   │   ├── __init__.py
│   │   ├── deps.py                 # API-specific deps
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # Asosiy router
│   │       ├── auth/
│   │       │   ├── routes.py
│   │       │   └── schemas.py
│   │       ├── users/
│   │       ├── academic/
│   │       ├── courses/
│   │       ├── content/
│   │       ├── assignments/
│   │       ├── live/
│   │       ├── exams/
│   │       ├── payments/
│   │       ├── reports/
│   │       └── webhooks/           # Tashqi webhook'lar
│   │
│   ├── modules/                    # Domain logic (DDD)
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # SQLAlchemy
│   │   │   ├── schemas.py          # Pydantic
│   │   │   ├── service.py          # Business logic
│   │   │   ├── repository.py       # DB queries
│   │   │   └── exceptions.py
│   │   ├── academic/
│   │   ├── enrollment/
│   │   ├── content/
│   │   ├── courses/
│   │   ├── assignments/
│   │   ├── live/
│   │   ├── exams/
│   │   ├── proctoring/
│   │   ├── payments/
│   │   ├── notifications/
│   │   └── reports/
│   │
│   ├── integrations/               # Tashqi xizmatlar
│   │   ├── __init__.py
│   │   ├── hemis/
│   │   │   ├── client.py
│   │   │   ├── schemas.py
│   │   │   └── sync.py
│   │   ├── zoom/
│   │   │   ├── client.py
│   │   │   ├── webhooks.py
│   │   │   └── schemas.py
│   │   ├── oneid/
│   │   ├── click/
│   │   ├── payme/
│   │   ├── eskiz/                  # SMS
│   │   ├── telegram/
│   │   ├── otjbat/
│   │   ├── tsdin/
│   │   └── antiplag/
│   │
│   ├── workers/                    # Celery tasks
│   │   ├── __init__.py
│   │   ├── video.py                # Transkodlash
│   │   ├── email.py
│   │   ├── sms.py
│   │   ├── hemis_sync.py
│   │   ├── reports.py
│   │   ├── proctoring.py
│   │   └── plagiarism.py
│   │
│   ├── utils/                      # Yordamchi funksiyalar
│   │   ├── __init__.py
│   │   ├── pagination.py
│   │   ├── pdf.py
│   │   ├── qr.py
│   │   ├── files.py
│   │   └── validators.py
│   │
│   └── websockets/                 # WebSocket handlers
│       ├── __init__.py
│       ├── chat.py
│       ├── notifications.py
│       └── live_proctoring.py
│
├── alembic/                        # DB migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── tests/                          # Testlar
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── scripts/                        # Yordamchi skriptlar
    ├── seed.py                     # Test ma'lumotlar
    ├── create_superuser.py
    └── migrate_data.py
```

## Frontend tuzilmasi

```
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── index.html
├── Dockerfile
├── nginx.conf                      # Production uchun
├── .env.example
│
├── public/
│   ├── favicon.ico
│   └── robots.txt
│
├── src/
│   ├── main.ts                     # Entry point
│   ├── App.vue
│   │
│   ├── assets/
│   │   ├── images/
│   │   ├── fonts/
│   │   └── styles/
│   │       ├── main.css
│   │       └── tailwind.css
│   │
│   ├── components/                 # Umumiy komponentlar
│   │   ├── ui/                     # Asosiy UI (button, input, modal)
│   │   │   ├── Button.vue
│   │   │   ├── Input.vue
│   │   │   ├── Modal.vue
│   │   │   ├── Card.vue
│   │   │   └── Table.vue
│   │   ├── layout/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppFooter.vue
│   │   │   └── AppLayout.vue
│   │   ├── auth/
│   │   ├── courses/
│   │   ├── exams/
│   │   ├── live/
│   │   └── shared/
│   │       ├── Loading.vue
│   │       ├── EmptyState.vue
│   │       └── ErrorBoundary.vue
│   │
│   ├── views/                      # Sahifalar
│   │   ├── auth/
│   │   │   ├── LoginView.vue
│   │   │   ├── RegisterView.vue
│   │   │   └── ResetPasswordView.vue
│   │   ├── dashboard/
│   │   ├── courses/
│   │   ├── exams/
│   │   ├── live/
│   │   ├── profile/
│   │   ├── admin/
│   │   └── public/
│   │
│   ├── router/
│   │   ├── index.ts
│   │   ├── routes.ts
│   │   └── guards.ts               # Auth guard, permission guard
│   │
│   ├── stores/                     # Pinia stores
│   │   ├── auth.ts
│   │   ├── user.ts
│   │   ├── courses.ts
│   │   ├── notifications.ts
│   │   └── ui.ts
│   │
│   ├── api/                        # Axios klient
│   │   ├── client.ts               # Axios instance
│   │   ├── interceptors.ts
│   │   ├── auth.ts
│   │   ├── courses.ts
│   │   ├── exams.ts
│   │   └── ...
│   │
│   ├── composables/                # Vue 3 composables
│   │   ├── useAuth.ts
│   │   ├── usePermissions.ts
│   │   ├── useToast.ts
│   │   ├── useWebSocket.ts
│   │   └── useDebounce.ts
│   │
│   ├── i18n/
│   │   ├── index.ts
│   │   └── locales/
│   │       ├── uz-lat.json
│   │       ├── uz-cyr.json
│   │       ├── ru.json
│   │       └── en.json
│   │
│   ├── types/                      # TypeScript types
│   │   ├── api.d.ts
│   │   ├── models.d.ts
│   │   └── index.d.ts
│   │
│   └── utils/
│       ├── format.ts               # Date, number formatting
│       ├── validation.ts
│       ├── storage.ts
│       └── constants.ts
│
└── tests/
    ├── unit/
    └── e2e/                        # Playwright
```

## Infrastructure tuzilmasi

```
infra/
├── docker/
│   ├── nginx/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   ├── postgres/
│   │   ├── Dockerfile
│   │   └── init.sql
│   └── redis/
│       └── redis.conf
│
├── k8s/                            # Kubernetes manifestlar
│   ├── base/                       # Asosiy
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── redis-statefulset.yaml
│   │   ├── minio-statefulset.yaml
│   │   ├── ingress.yaml
│   │   └── hpa.yaml                # HorizontalPodAutoscaler
│   ├── overlays/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── kustomization.yaml
│
├── helm/                           # Helm chart (alternativ)
│   └── lms/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│
├── terraform/                      # IaC (cloud uchun)
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
│
└── monitoring/
    ├── prometheus/
    │   └── prometheus.yml
    ├── grafana/
    │   └── dashboards/
    └── alertmanager/
        └── alertmanager.yml
```

## Skripts papkasi

```
scripts/
├── dev/
│   ├── setup.sh                    # Dev muhit ishga tushirish
│   ├── reset-db.sh
│   └── seed-data.sh
├── deploy/
│   ├── build.sh
│   └── deploy.sh
└── tools/
    ├── generate-openapi.sh
    └── backup-db.sh
```

## Git ignore tavsiyalari

`.gitignore` quyidagilarni o'z ichiga olishi kerak:
- `__pycache__/`, `*.pyc`
- `node_modules/`, `dist/`
- `.env`, `.env.local`
- `*.log`
- `.venv/`, `venv/`
- `.idea/`, `.vscode/` (jamoaviy sozlamalar emas)
- `coverage/`, `.pytest_cache/`
- `media/`, `uploads/` (production fayllar)
