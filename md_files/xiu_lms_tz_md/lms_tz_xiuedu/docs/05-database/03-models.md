# 03. SQLAlchemy Modellar

## Maqsad

SQLAlchemy 2.0 (async) bilan ishlash. Modellar, repository pattern, query patterns.

## Asosiy konfiguratsiya

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from app.core.config import settings


class Base(DeclarativeBase):
    """Asosiy model class"""
    pass


# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

## Mixins

```python
# app/core/mixins.py
from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditMixin:
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )


class TenantMixin:
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
```

## Model misollari

### User
```python
# app/modules/users/models.py
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.mixins import IdMixin, TimestampMixin, SoftDeleteMixin


class User(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    
    password_hash: Mapped[str | None] = mapped_column(String(255))
    
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relations
    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, lazy="selectin")
    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
```

### Course (multi-tenant)
```python
# app/modules/courses/models.py

class Course(Base, IdMixin, TimestampMixin, AuditMixin, TenantMixin):
    __tablename__ = "courses"
    
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    subject_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subjects.id"))
    
    duration_weeks: Mapped[int] = mapped_column(Integer, default=16)
    credits: Mapped[float] = mapped_column(Numeric(5, 2), default=4.0)
    
    primary_author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    
    # Relations
    subject: Mapped["Subject"] = relationship(lazy="joined")
    author: Mapped["User"] = relationship(foreign_keys=[primary_author_id])
    modules: Mapped[list["CourseModule"]] = relationship(
        back_populates="course",
        order_by="CourseModule.order_index",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")
    
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_courses_org_code"),
    )
```

## Repository pattern

```python
# app/modules/courses/repository.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from .models import Course


class CourseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, course_id: int) -> Course | None:
        result = await self.session.execute(
            select(Course)
            .options(
                selectinload(Course.modules),
                joinedload(Course.subject),
            )
            .where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_org(
        self,
        organization_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Course], int]:
        # Query
        query = select(Course).where(Course.organization_id == organization_id)
        if status:
            query = query.where(Course.status == status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        # Pagination
        query = query.limit(limit).offset(offset).order_by(Course.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars()), total or 0
    
    async def search(
        self,
        organization_id: int,
        query: str,
    ) -> list[Course]:
        result = await self.session.execute(
            select(Course)
            .where(Course.organization_id == organization_id)
            .where(
                func.to_tsvector("uzbek", Course.title + " " + Course.description)
                .match(query)
            )
        )
        return list(result.scalars())
    
    async def create(self, data: dict) -> Course:
        course = Course(**data)
        self.session.add(course)
        await self.session.flush()
        return course
    
    async def update(self, course: Course, data: dict) -> Course:
        for key, value in data.items():
            setattr(course, key, value)
        await self.session.flush()
        return course
    
    async def delete(self, course: Course) -> None:
        await self.session.delete(course)
        await self.session.flush()
```

## Service layer

```python
# app/modules/courses/service.py

class CourseService:
    def __init__(self, repo: CourseRepository, current_user: User):
        self.repo = repo
        self.user = current_user
    
    async def create_course(self, data: CourseCreateSchema) -> Course:
        # Permission check
        if not has_permission(self.user, "course.create"):
            raise PermissionDenied()
        
        # Business logic
        if await self.repo.exists_by_code(data.organization_id, data.code):
            raise ValidationError("Code already exists")
        
        # Create
        course = await self.repo.create({
            **data.dict(),
            "created_by": self.user.id,
            "primary_author_id": data.primary_author_id or self.user.id,
        })
        
        # Side effects (notifications, etc.)
        await notify_course_created(course)
        
        return course
```

## Eager loading patterns

### selectin loading (1+1 query, recommended for collections)
```python
result = await session.execute(
    select(User).options(selectinload(User.roles), selectinload(User.profile))
)
```

### joined loading (1 query, for single relations)
```python
result = await session.execute(
    select(Course).options(joinedload(Course.subject))
)
```

### Avoid lazy loading in async!
```python
# YOMON
user = await session.get(User, 1)
print(user.profile.name)  # MissingGreenlet error!

# YAXSHI
result = await session.execute(
    select(User).options(selectinload(User.profile)).where(User.id == 1)
)
user = result.scalar_one()
print(user.profile.name)  # OK
```

## Common queries

### Aggregations
```python
from sqlalchemy import func

# Count
total = await session.scalar(select(func.count()).select_from(User))

# Group by
result = await session.execute(
    select(Course.status, func.count(Course.id))
    .group_by(Course.status)
)
```

### Window functions
```python
from sqlalchemy import over, func

# Talabaning kursdagi joyini topish
query = select(
    Student.id,
    Student.full_name,
    Student.gpa,
    func.row_number().over(order_by=Student.gpa.desc()).label("rank"),
).where(Student.specialty_id == specialty_id)
```

### CTEs (Common Table Expressions)
```python
# Active studentlarni topish va ularning kurslarini hisoblash
active_students_cte = (
    select(Student.id, Student.user_id)
    .where(Student.status == "active")
    .cte("active_students")
)

result = await session.execute(
    select(active_students_cte.c.id, func.count(Enrollment.id))
    .join(Enrollment, Enrollment.user_id == active_students_cte.c.user_id)
    .group_by(active_students_cte.c.id)
)
```

## Bulk operations

### Bulk insert
```python
from sqlalchemy import insert

await session.execute(
    insert(Notification),
    [
        {"user_id": 1, "title": "Hi"},
        {"user_id": 2, "title": "Hi"},
        # ...
    ]
)
```

### Bulk update
```python
from sqlalchemy import update

await session.execute(
    update(User)
    .where(User.is_active == False)
    .values(deleted_at=datetime.utcnow())
)
```

## Acceptance kriteriyalar

- [ ] SQLAlchemy 2.0 async pattern
- [ ] DeclarativeBase + Mapped types
- [ ] Mixins (Id, Timestamp, SoftDelete, Audit, Tenant)
- [ ] Repository pattern
- [ ] Service layer alohida
- [ ] Eager loading patterns (selectinload, joinedload)
- [ ] Bulk operations
- [ ] Proper async session handling
- [ ] Test coverage ≥ 80%
