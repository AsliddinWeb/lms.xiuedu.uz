# 07.04. Xavfsizlik (Security)

## Maqsad

Tizimni OWASP Top 10, ISO 27001 va O'zbekiston Respublikasi shaxsiy ma'lumotlarni himoya qilish to'g'risidagi qonun talablariga muvofiq himoya qilish.

## Normativ asoslar

- O'zbekiston Respublikasi "Shaxsga doir ma'lumotlar to'g'risida"gi qonun
- ISO/IEC 27001:2013 — Axborot xavfsizligi boshqaruv tizimlari
- OWASP Top 10 (2021)
- 559-son qaror — server O'zbekiston hududida bo'lishi shart

## Xavfsizlik darajalari

```
┌────────────────────────────────────────────────────┐
│ 1. Network Security (Firewall, DDoS, WAF)          │
├────────────────────────────────────────────────────┤
│ 2. Application Security (Auth, RBAC, Input Valid)  │
├────────────────────────────────────────────────────┤
│ 3. Data Security (Encryption at-rest, in-transit)  │
├────────────────────────────────────────────────────┤
│ 4. Infrastructure Security (Hardening, Patches)    │
├────────────────────────────────────────────────────┤
│ 5. Operational Security (Audit, Backup, IR)        │
└────────────────────────────────────────────────────┘
```

## 1. Network Security

### TLS/SSL

- Minimum TLS 1.2, ideal TLS 1.3
- Sertifikat: Let's Encrypt yoki UZINFOCOM
- HSTS (HTTP Strict Transport Security) yoqilgan
- Sertifikat avtomatik yangilanadi

`nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name lms.xiuedu.uz;

    ssl_certificate /etc/letsencrypt/live/lms.xiuedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lms.xiuedu.uz/privkey.pem;

    # Modern TLS config
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(self), camera=(self)" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://lms-cdn.xiuedu.uz; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss://lms.xiuedu.uz" always;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name lms.xiuedu.uz;
    return 301 https://$host$request_uri;
}
```

### DDoS himoyasi

`nginx.conf`:

```nginx
# Rate limiting zonalari
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=100r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    # Auth endpoints - 5 req/min
    location /api/auth/login {
        limit_req zone=auth_limit burst=3 nodelay;
        proxy_pass http://backend;
    }

    # API - 60 req/min
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 10;
        proxy_pass http://backend;
    }
}
```

### Firewall (UFW)

```bash
# Faqat kerakli portlar ochiq
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp        # SSH (faqat ma'lum IP'lardan)
ufw allow 80/tcp        # HTTP
ufw allow 443/tcp       # HTTPS
ufw enable

# SSH brute force himoyasi
fail2ban-client status sshd
```

## 2. Application Security

### Password policy

```python
# app/core/security.py
import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def validate_password(password: str) -> tuple[bool, str | None]:
    """Parol siyosati."""
    if len(password) < 12:
        return False, "Parol kamida 12 belgidan iborat bo'lishi kerak"

    if not re.search(r"[A-Z]", password):
        return False, "Parol kamida 1 ta katta harf bo'lishi kerak"

    if not re.search(r"[a-z]", password):
        return False, "Parol kamida 1 ta kichik harf bo'lishi kerak"

    if not re.search(r"\d", password):
        return False, "Parol kamida 1 ta raqam bo'lishi kerak"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Parol kamida 1 ta maxsus belgi bo'lishi kerak"

    # Common parollar
    common = {"password", "123456", "qwerty", "admin"}
    if password.lower() in common:
        return False, "Bu parol juda oddiy"

    return True, None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### SQL Injection himoyasi

```python
# YOMON - SQL Injection imkoniyati
query = f"SELECT * FROM users WHERE email = '{email}'"

# YAXSHI - parametrlangan so'rov (SQLAlchemy)
result = await db.execute(
    select(User).where(User.email == email)
)
```

### XSS himoyasi

```python
# Input validation
from pydantic import BaseModel, validator
import bleach

class CommentCreate(BaseModel):
    content: str

    @validator("content")
    def sanitize_content(cls, v: str) -> str:
        # HTML taglarni olib tashlash
        return bleach.clean(
            v,
            tags=["p", "br", "strong", "em", "ul", "ol", "li"],
            attributes={},
            strip=True
        )
```

### CSRF himoyasi

```python
# JWT token Authorization header'da yuboriladi - cookie emas
# CORS qattiq sozlangan

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lms.xiuedu.uz",        # Talaba/o'qituvchi frontend
        "https://lms-admin.xiuedu.uz",  # Admin panel
    ],  # YULGIZ '*' EMAS
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
```

### Brute force himoyasi

```python
# app/services/auth_service.py
from app.core.cache import redis_client

async def check_login_attempts(identifier: str) -> bool:
    """5 marta noto'g'ri urinishdan keyin 15 daqiqaga blok."""
    key = f"login_attempts:{identifier}"
    attempts = await redis_client.get(key)

    if attempts and int(attempts) >= 5:
        ttl = await redis_client.ttl(key)
        raise HTTPException(
            429,
            f"Juda ko'p urinish. {ttl // 60} daqiqadan keyin urinib ko'ring"
        )
    return True

async def record_failed_login(identifier: str):
    key = f"login_attempts:{identifier}"
    await redis_client.incr(key)
    await redis_client.expire(key, 900)  # 15 daqiqa

async def reset_login_attempts(identifier: str):
    await redis_client.delete(f"login_attempts:{identifier}")
```

## 3. Data Security

### Encryption at-rest

PostgreSQL'da nozik ma'lumotlarni shifrlash:

```python
# app/core/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()

# Modelda ishlatish
from sqlalchemy.types import TypeDecorator, String

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt(value)

# User model
class User(Base):
    passport_pinfl: Mapped[str] = mapped_column(EncryptedString(255))
```

### Disk encryption

```bash
# LUKS bilan disk shifrlash
cryptsetup luksFormat /dev/sdb
cryptsetup luksOpen /dev/sdb encrypted_data
mkfs.ext4 /dev/mapper/encrypted_data
```

### Backup encryption

```bash
# Backup'ni shifrlab saqlash
pg_dump -U lms_user lms_db | gzip | gpg --encrypt --recipient backup@xiuedu.uz > backup.sql.gz.gpg
```

## 4. Infrastructure Security

### OS Hardening

```bash
# Avtomatik xavfsizlik yangilanishlari
apt install unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades

# SSH qattiqlashtirish
# /etc/ssh/sshd_config:
PermitRootLogin no
PasswordAuthentication no  # Faqat SSH key
AllowUsers admin deploy
MaxAuthTries 3
ClientAliveInterval 300
```

### Container security

```dockerfile
# Non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Read-only filesystem
# docker-compose.yml:
#   read_only: true
#   tmpfs:
#     - /tmp
```

### Secrets management

- **Hashicorp Vault** yoki **AWS Secrets Manager**
- `.env` fayllar production'da ishlatilmaydi
- Docker secrets yoki Kubernetes Secrets

```yaml
# docker-compose.yml
services:
  backend:
    secrets:
      - jwt_secret
      - db_password

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_password:
    file: ./secrets/db_password.txt
```

## 5. Operational Security

### Audit logging

```python
# app/models/audit_log.py
class AuditLog(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))  # login, update_profile, etc.
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(default=func.now())

# Decorator
def audit(action: str, resource_type: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            user = kwargs.get("current_user")
            result = await func(*args, **kwargs)

            await create_audit_log(
                user_id=user.id if user else None,
                action=action,
                resource_type=resource_type,
                resource_id=str(result.id) if hasattr(result, "id") else None,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent", ""),
            )
            return result
        return wrapper
    return decorator

# Foydalanish
@audit(action="update", resource_type="user")
async def update_user(user_id: UUID, ...): ...
```

### Backup strategy

| Backup turi | Chastota | Saqlash muddati | Joy |
|-------------|----------|-----------------|-----|
| Full DB | Har kuni 02:00 | 30 kun | S3 + lokal |
| Incremental DB | Har soatda | 7 kun | Lokal |
| Files (MinIO) | Har kuni | 30 kun | S3 |
| Configuration | Har deploy | Cheksiz | Git |

```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/backups/$(date +%Y/%m/%d)"
mkdir -p $BACKUP_DIR

# DB backup
pg_dump -U lms_user lms_db | gzip | \
  gpg --encrypt --recipient backup@xiuedu.uz > \
  $BACKUP_DIR/lms_db_$(date +%H%M).sql.gz.gpg

# MinIO sync
mc mirror --overwrite minio/lms-files $BACKUP_DIR/files/

# S3 ga yuborish
aws s3 sync $BACKUP_DIR s3://lms-backups/$(date +%Y/%m/%d)/

# Eski backup'larni o'chirish
find /backups -type d -mtime +30 -exec rm -rf {} \;
```

### Incident Response Plan

1. **Aniqlash** — Sentry/Alert orqali signal
2. **Ajratish** — zararlangan tizim/foydalanuvchini ajratish
3. **Tekshirish** — log analiz
4. **Bartaraf etish** — patch, parol almashtirish
5. **Tiklash** — backup'dan tiklash
6. **Hisobot** — incident report yozish

## Penetration Testing

- Yiliga 1 marta — tashqi audit
- Avtomatik scan'lar (OWASP ZAP, Trivy) — har deploy

## GDPR / Shaxsiy ma'lumotlar

- Foydalanuvchining "Right to be forgotten" — `DELETE /api/users/me`
- Ma'lumotlarni eksport qilish — `GET /api/users/me/export`
- Cookie consent banner
- Privacy policy va Terms of Service

## Acceptance kriteriyalar

- [ ] TLS 1.2+ majburiy, HSTS yoqilgan
- [ ] Barcha xavfsizlik headerlari sozlangan
- [ ] Rate limiting har bir endpoint'da
- [ ] Argon2 password hashing
- [ ] Brute force himoyasi (5 attempts)
- [ ] Audit log barcha muhim amallar uchun
- [ ] Avtomatik backup va shifrlash
- [ ] Secrets Vault'da saqlanadi
- [ ] OWASP ZAP scan natijalari toza
- [ ] Penetration test yiliga 1 marta
- [ ] Server O'zbekiston hududida (559-qaror talabi)
