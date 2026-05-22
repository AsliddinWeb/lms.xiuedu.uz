# 02. Migrations (Alembic)

## Maqsad

Database schema'ni versiyalash, deploy qilish, rollback qilish.

## Tool

**Alembic** — SQLAlchemy uchun standart migration tool.

## Sozlash

### `alembic.ini`
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/lms_db

[loggers]
keys = root,sqlalchemy,alembic
```

### `alembic/env.py`
```python
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.database import Base
from app.core.config import settings

# Barcha modellarni import (autogenerate uchun)
from app.modules.users.models import *
from app.modules.courses.models import *
# ...

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
    )
    
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


run_migrations_online()
```

## Migration yaratish

### Autogenerate (modellar o'zgargandan keyin)
```bash
alembic revision --autogenerate -m "add courses table"
```

### Bo'sh migration
```bash
alembic revision -m "custom data migration"
```

## Migration shabloni

```python
"""add courses table

Revision ID: 7a1b2c3d4e5f
Revises: 6f5e4d3c2b1a
Create Date: 2026-05-01 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '7a1b2c3d4e5f'
down_revision = '6f5e4d3c2b1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'courses',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.UniqueConstraint('organization_id', 'code', name='uq_courses_org_code'),
    )
    op.create_index('idx_courses_status', 'courses', ['status'])


def downgrade() -> None:
    op.drop_index('idx_courses_status', 'courses')
    op.drop_table('courses')
```

## Buyruqlar

```bash
# Joriy holatni ko'rish
alembic current

# Tarix
alembic history

# Yangilash (oxirgi versiyaga)
alembic upgrade head

# Bitta yuqoriga
alembic upgrade +1

# Bitta pastga
alembic downgrade -1

# Aniq versiyaga
alembic upgrade 7a1b2c3d4e5f

# Boshiga (ehtiyot bo'ling!)
alembic downgrade base

# SQL ko'rish (ishga tushirmasdan)
alembic upgrade head --sql
```

## Production deploy strategiyasi

### 1. Zero-downtime deploy

Migration deploy bo'layotgan kodga muvofiq bo'lishi kerak:

**Yangi ustun qo'shish (xavfsiz):**
```python
# Migration 1: ustun qo'shish (NULL allowed)
op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

# Deploy code
# Migration 2 (ixtiyoriy): default qiymat to'ldirish
# Migration 3: NOT NULL (agar kerak bo'lsa)
op.alter_column('users', 'phone', nullable=False)
```

**Ustun o'chirish (xavfli):**
```python
# Migration 1: kod allaqachon bu ustun ishlatmasligi kerak
op.drop_column('users', 'old_field')
```

**Ustun tipini o'zgartirish:**
```python
# Yangi ustun yaratish, ma'lumotni ko'chirish, eski ustunni olib tashlash
# 3 alohida migration
```

### 2. Data migration

```python
def upgrade():
    # Schema migration
    op.add_column('users', sa.Column('full_name', sa.String(200)))
    
    # Data migration
    connection = op.get_bind()
    connection.execute(
        "UPDATE users SET full_name = first_name || ' ' || last_name"
    )
    
    # Now mark NOT NULL
    op.alter_column('users', 'full_name', nullable=False)
```

### 3. Katta jadvallar uchun

```python
# Lock'siz index qo'shish
op.execute("CREATE INDEX CONCURRENTLY idx_users_email ON users(email)")
op.execute("ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE USING INDEX idx_users_email")

# Bilan transaction'siz
def upgrade():
    op.execute("COMMIT")
    op.execute("CREATE INDEX CONCURRENTLY ...")
```

## Partitioning migrations

```python
def upgrade():
    op.execute("""
        CREATE TABLE audit_logs (
            id BIGSERIAL,
            user_id BIGINT,
            action VARCHAR(100),
            created_at TIMESTAMP NOT NULL,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)
    
    # Birinchi partition
    op.execute("""
        CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    
    # pg_partman avtomatik
    op.execute("""
        SELECT partman.create_parent(
            'public.audit_logs', 'created_at', 'native', 'monthly'
        )
    """)
```

## Rollback strategiyasi

### Avtomatik rollback (failed deploy)
```yaml
# CI/CD pipeline
- name: Run migrations
  run: alembic upgrade head
  
- name: Run smoke tests
  run: pytest tests/smoke/

- name: Rollback if failed
  if: failure()
  run: alembic downgrade -1
```

### Manual rollback
```bash
# Joriy versiya
alembic current

# Avvalgi versiyaga
alembic downgrade -1

# Aniq versiyaga
alembic downgrade abc123def456
```

## Best practices

1. **Doim downgrade()'ni yozing** — production'da rollback kerak bo'lishi mumkin
2. **Autogenerate'ni tekshiring** — `alembic revision --autogenerate` keyin migration faylni qo'lda tahrirlang
3. **Katta data migration'larni alohida script'da qiling** — Alembic kichik DDL'lar uchun
4. **Production'da CONCURRENTLY ishlating** — index qo'shish/o'chirish uchun
5. **Schema o'zgarishlarini bosqichma-bosqich qiling** — kod va schema bir xil deployda bo'lishi shart emas
6. **Indexlar uchun alohida migration** — sekin operatsiyalar
7. **Test environmentda doim sinang** — staging environmentda

## Acceptance kriteriyalar

- [ ] Alembic sozlangan
- [ ] Async PostgreSQL bilan ishlaydi
- [ ] Autogenerate ishlaydi
- [ ] Production deploy strategiyasi
- [ ] Rollback har bir migrationda
- [ ] CI/CD pipeline integratsiya
- [ ] Partitioning migrationlar
- [ ] Concurrent index yaratish
- [ ] Data migration patterns
