# 11. Communications (Kommunikatsiya) Moduli

## Maqsad

Foydalanuvchilar oʻrtasida muloqot: chat, forum, email, SMS, push, Telegram bot.

## Funksional talablar

### 1. Real-time chat

- 1-to-1 chat (talaba ↔ pedagog)
- Guruh chati (kurs talabalari, kafedra)
- Xabar yuborish (matn, fayl, rasm, ovozli xabar)
- Read receipts (ko'rilgan)
- Typing indicators
- Online/offline holati
- Emoji va reaktsiyalar
- Xabarni o'chirish, tahrirlash
- Search xabarlar ichida

### 2. Forum / Discussion

Har bir kurs ichida forum:
- Mavzular yaratish (talaba/pedagog)
- Javob yozish (threaded)
- Markdown formatlash
- Rasm/fayl qo'shish
- Like / dislike
- Best answer (pedagog belgilaydi)
- Search
- Mention (@username)

### 3. E-mail xabarnomalar

Avtomatik email yuboriladi:
- Ro'yxatdan o'tish tasdiqlash
- Parolni tiklash
- Yangi vazifa
- Vazifa baholandi
- Imtihon yaqinlashdi
- Live dars boshlanmoqda
- To'lov reminderi
- Kontrakt tasdiqlash

**Texnik:** SMTP (mahalliy) + SendGrid (backup), HTML shablonlari (Jinja2).

### 4. SMS xabarnomalar

Eskiz.uz orqali:
- 2FA kod
- Yangi parol
- Imtihon vaqti
- To'lov reminderi (3 kun, 1 kun oldin)
- Muhim bayonotlar

### 5. Push notifications

Web push va mobile push:
- Real-time hodisalar
- Yangi xabar
- Live dars boshlanishi
- Imtihon ogohlantirishi
- Vazifa bahosi

**Texnik:** Web Push (VAPID), FCM (Android/iOS).

### 6. Telegram bot

@OliyLMSBot:
- Bot bilan akkauntni bog'lash (verification code)
- Kunlik dars jadvali
- Yangi xabarnomalar
- Imtihon natijalari
- Quick balance check
- Test sinov rejimi

### 7. Bildirishnoma sozlamalari

Foydalanuvchi tanlay oladi:
- Kanal: email / SMS / push / Telegram
- Hodisa turlari (har biri alohida toggle)
- Quiet hours (22:00 — 08:00)
- Tilni tanlash

### 8. Inbox tizimi

- Centralizatsiyalashgan xabarlar inbox'i
- Filter: barcha / o'qilmagan / muhim
- Markirovka: muhim, arxiv
- Ommaviy harakatlar (mark all read)

## API Endpoints

```
# Chat
GET    /api/v1/chats                          # mening chatlarim
POST   /api/v1/chats                          # yangi chat
GET    /api/v1/chats/{id}/messages
POST   /api/v1/chats/{id}/messages
PATCH  /api/v1/messages/{id}                  # tahrir
DELETE /api/v1/messages/{id}
POST   /api/v1/messages/{id}/read

WS     /ws/chat                               # real-time

# Forum
GET    /api/v1/courses/{id}/forum/topics
POST   /api/v1/courses/{id}/forum/topics
GET    /api/v1/forum/topics/{id}
GET    /api/v1/forum/topics/{id}/posts
POST   /api/v1/forum/topics/{id}/posts
POST   /api/v1/forum/posts/{id}/like
POST   /api/v1/forum/posts/{id}/best-answer

# Bildirishnomalar
GET    /api/v1/notifications                  # ro'yxat
GET    /api/v1/notifications/unread-count
POST   /api/v1/notifications/{id}/read
POST   /api/v1/notifications/mark-all-read
GET    /api/v1/notifications/preferences
PATCH  /api/v1/notifications/preferences

# Push subscription
POST   /api/v1/push/subscribe
DELETE /api/v1/push/subscribe

# Telegram bot
POST   /api/v1/telegram/connect               # bog'lash kodi yaratish
POST   /api/v1/telegram/webhook               # bot webhook
DELETE /api/v1/telegram/disconnect
```

## Database modellari

```sql
-- Chat (xona)
CREATE TABLE chats (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL,                     -- 'direct', 'group', 'course'
    name VARCHAR(200),                             -- group/course uchun
    course_id BIGINT REFERENCES courses(id),
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat ishtirokchilari
CREATE TABLE chat_members (
    chat_id BIGINT REFERENCES chats(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member',             -- 'admin', 'member'
    joined_at TIMESTAMP DEFAULT NOW(),
    last_read_message_id BIGINT,
    PRIMARY KEY (chat_id, user_id)
);

-- Xabar
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats(id) ON DELETE CASCADE,
    sender_id BIGINT REFERENCES users(id),
    
    type VARCHAR(20) DEFAULT 'text',               -- 'text', 'file', 'image', 'voice', 'system'
    content TEXT,
    attachments JSONB,                             -- [{name, url, size}]
    
    reply_to_id BIGINT REFERENCES messages(id),
    
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_messages_chat ON messages(chat_id, created_at DESC);

-- Forum mavzular
CREATE TABLE forum_topics (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    
    author_id BIGINT REFERENCES users(id),
    
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    
    posts_count INT DEFAULT 0,
    views_count INT DEFAULT 0,
    
    last_activity_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Forum postlari
CREATE TABLE forum_posts (
    id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT REFERENCES forum_topics(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES forum_posts(id),   -- threading uchun
    
    author_id BIGINT REFERENCES users(id),
    content TEXT NOT NULL,
    attachments JSONB,
    
    is_best_answer BOOLEAN DEFAULT FALSE,
    likes_count INT DEFAULT 0,
    
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- Bildirishnoma
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    type VARCHAR(50) NOT NULL,                     -- 'assignment_new', 'grade_posted', 'live_starting', etc.
    title VARCHAR(500) NOT NULL,
    body TEXT,
    
    -- Bog'liq resurs
    resource_type VARCHAR(50),                     -- 'assignment', 'course', 'live_session'
    resource_id BIGINT,
    action_url TEXT,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Yetkazib berish
    channels TEXT[],                               -- ['inapp', 'email', 'sms', 'push', 'telegram']
    delivery_status JSONB DEFAULT '{}',            -- har channel uchun status
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);

-- Bildirishnoma sozlamalari
CREATE TABLE notification_preferences (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Channel preferences
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT TRUE,
    push_enabled BOOLEAN DEFAULT TRUE,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    
    -- Quiet hours
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    
    -- Per-event toggles
    event_preferences JSONB DEFAULT '{}',
    
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Push subscriptions
CREATE TABLE push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh VARCHAR(255),
    auth VARCHAR(255),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Telegram bog'lanish
CREATE TABLE telegram_accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    chat_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    connected_at TIMESTAMP DEFAULT NOW()
);
```

## Notification service

```python
# app/modules/notifications/service.py

class NotificationService:
    async def send(
        self,
        user_id: int,
        type: str,
        title: str,
        body: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        channels: list[str] | None = None,
    ):
        """Multi-channel notification yuborish"""
        
        # Foydalanuvchi sozlamalarini olish
        prefs = await self.repo.get_preferences(user_id)
        
        # Channels filter (foydalanuvchi sozlamalariga muvofiq)
        channels = channels or self._default_channels(type)
        active_channels = self._filter_channels(channels, prefs, type)
        
        # Notificationni saqlash
        notification = await self.repo.create_notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
            channels=active_channels,
        )
        
        # Har channelga yuborish (Celery)
        for channel in active_channels:
            if channel == "email":
                from app.workers.email import send_email
                send_email.delay(user_id, title, body)
            elif channel == "sms":
                from app.workers.sms import send_sms
                send_sms.delay(user_id, body)
            elif channel == "push":
                from app.workers.push import send_push
                send_push.delay(user_id, title, body)
            elif channel == "telegram":
                from app.workers.telegram import send_telegram
                send_telegram.delay(user_id, body)
        
        return notification
```

## WebSocket chat

```python
# app/websockets/chat.py
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(ws)
    
    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self.connections:
            self.connections[user_id].remove(ws)
    
    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                await ws.send_json(message)


manager = ConnectionManager()

@app.websocket("/ws/chat")
async def chat_ws(ws: WebSocket, user: User = Depends(get_user_from_token)):
    await manager.connect(user.id, ws)
    
    try:
        while True:
            data = await ws.receive_json()
            
            # Save message
            msg = await save_message(
                chat_id=data["chat_id"],
                sender_id=user.id,
                content=data["content"],
            )
            
            # Notify all chat members
            members = await get_chat_members(data["chat_id"])
            for member in members:
                await manager.send_to_user(member.user_id, {
                    "type": "new_message",
                    "message": msg.dict(),
                })
                
    except WebSocketDisconnect:
        manager.disconnect(user.id, ws)
```

## Telegram bot

```python
# app/integrations/telegram/bot.py
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Salom! Men Oliy LMS botiman.\n\n"
        "Bog'lanish uchun /connect <kod> buyrug'ini kiriting.\n"
        "Kodni profil sahifasidan olishingiz mumkin."
    )

@dp.message(Command("connect"))
async def cmd_connect(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Iltimos, kodni kiriting: /connect <kod>")
        return
    
    code = args[1]
    user = await find_user_by_telegram_code(code)
    
    if not user:
        await message.answer("❌ Noto'g'ri yoki muddati tugagan kod")
        return
    
    await link_telegram_account(user.id, message.chat.id, message.from_user.username)
    await message.answer(f"✅ Hisobingiz bog'landi: {user.full_name}")

@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    user = await get_user_by_chat_id(message.chat.id)
    if not user:
        await message.answer("Avval /connect orqali bog'laning")
        return
    
    schedule = await get_today_schedule(user.id)
    text = "📅 Bugungi jadval:\n\n"
    for item in schedule:
        text += f"• {item.time} — {item.title}\n"
    
    await message.answer(text)
```

## Acceptance kriteriyalar

- [ ] Real-time chat (WebSocket)
- [ ] 1-to-1 va guruh chatlari
- [ ] Forum (kurs ichida)
- [ ] Email yuborish (SMTP + SendGrid backup)
- [ ] SMS (Eskiz.uz)
- [ ] Web Push notification
- [ ] Telegram bot
- [ ] Multi-channel notification service
- [ ] Foydalanuvchi sozlamalari
- [ ] Quiet hours
- [ ] Inbox UI
- [ ] Test coverage ≥ 75%
