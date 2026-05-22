-- Postgres initial setup. Bu fayl konteyner birinchi marta ko'tarilganda ishlaydi.

-- Foydalaniladigan extensiyalar
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- full-text uchun
CREATE EXTENSION IF NOT EXISTS "citext";         -- case-insensitive text
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- composite indexlar uchun
