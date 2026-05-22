# 07.02. CI/CD Pipeline

## Maqsad

Kodni avtomatik tarzda test qilish, build qilish va deploy qilish jarayonini avtomatlashtirish.

## Pipeline arxitekturasi

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Push   │───▶│  Lint   │───▶│  Test   │───▶│  Build  │───▶│ Deploy  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                    │              │              │              │
                    ▼              ▼              ▼              ▼
                 Ruff,         Pytest,        Docker         Staging /
                 Black,        Vitest,        Image          Production
                 ESLint        E2E
```

## GitHub Actions

### Backend pipeline

`.github/workflows/backend.yml`:

```yaml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: registry.xiuedu.uz
  IMAGE_NAME: lms-backend

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install poetry==1.7.1
          poetry install --no-interaction

      - name: Run Ruff
        working-directory: ./backend
        run: poetry run ruff check .

      - name: Run Black
        working-directory: ./backend
        run: poetry run black --check .

      - name: Run MyPy
        working-directory: ./backend
        run: poetry run mypy app/

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install poetry==1.7.1
          poetry install --no-interaction

      - name: Run migrations
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_password@localhost:5432/test_db
        run: poetry run alembic upgrade head

      - name: Run pytest
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_password@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test-secret
        run: |
          poetry run pytest \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit
        uses: shundor/python-bandit-scan@v1
        with:
          path: ./backend

      - name: Run Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: './backend'
          severity: 'CRITICAL,HIGH'

  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Scan image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'

  deploy_staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Staging
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/lms
            docker-compose pull backend
            docker-compose up -d backend
            docker-compose exec -T backend alembic upgrade head

  deploy_production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Production
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/lms
            docker-compose pull backend
            docker-compose up -d --no-deps backend
            docker-compose exec -T backend alembic upgrade head

      - name: Notify Telegram
        uses: appleboy/telegram-action@master
        with:
          to: ${{ secrets.TELEGRAM_CHAT_ID }}
          token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          message: |
            ✅ Backend deployed to production
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}
```

### Frontend pipeline

`.github/workflows/frontend.yml`:

```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: npm install -g pnpm

      - name: Install dependencies
        working-directory: ./frontend
        run: pnpm install --frozen-lockfile

      - name: Lint
        working-directory: ./frontend
        run: pnpm lint

      - name: Type check
        working-directory: ./frontend
        run: pnpm type-check

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        run: npm install -g pnpm

      - name: Install dependencies
        working-directory: ./frontend
        run: pnpm install --frozen-lockfile

      - name: Run unit tests
        working-directory: ./frontend
        run: pnpm test:unit --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/coverage-final.json
          flags: frontend

  e2e:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        run: npm install -g pnpm

      - name: Install dependencies
        working-directory: ./frontend
        run: pnpm install --frozen-lockfile

      - name: Install Playwright
        working-directory: ./frontend
        run: pnpm exec playwright install --with-deps chromium

      - name: Build
        working-directory: ./frontend
        run: pnpm build

      - name: Run E2E tests
        working-directory: ./frontend
        run: pnpm test:e2e

      - name: Upload Playwright report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30

  build:
    runs-on: ubuntu-latest
    needs: [test, e2e]
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Build & Push Docker Image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: registry.xiuedu.uz/lms-frontend:${{ github.sha }}
```

## Branch strategy

```
main          ─── Production (faqat tagged releases)
  │
  └── develop ─── Staging
        │
        ├── feature/auth-2fa
        ├── feature/exam-proctoring
        └── bugfix/payment-error
```

### Pull Request shartlari

- [ ] Barcha CI testlari yashil
- [ ] Code coverage ≥ 80%
- [ ] Kamida 1 reviewer approve qilgan
- [ ] Conflict yo'q
- [ ] Branch up-to-date

## Acceptance kriteriyalar

- [ ] Har bir push'da testlar avtomatik ishlaydi
- [ ] PR'larda lint/test natijalari ko'rinadi
- [ ] Develop branch staging'ga avto-deploy bo'ladi
- [ ] Main branch production'ga avto-deploy bo'ladi (approval bilan)
- [ ] Docker image'lar registry'ga push qilinadi
- [ ] Security scan har deploy'da o'tkaziladi
- [ ] Rollback imkoniyati mavjud
- [ ] Deploy haqida Telegram'ga xabar yuboriladi
