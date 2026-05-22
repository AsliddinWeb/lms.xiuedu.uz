# 10. Payments (Toʻlovlar) Moduli

## Maqsad

Talabalardan to'lov-kontrakt asosida pul olish, kontraktni boshqarish, qarzlarni kuzatish, Click va Payme bilan integratsiya.

## Normativ asos
- **VM 559-qaror Nizom 13-band:** Masofaviy ta'lim toʻlov-kontrakt asosida amalga oshiriladi

## Funksional talablar

### 1. Toʻlov tizimlari

| Provayder | Holati | Foydalanish |
|-----------|--------|-------------|
| **Click** | Asosiy | Karta + walletlar |
| **Payme** | Asosiy | Karta + Subscribe |
| **Apelsin** | Ikkinchi darajali | Apelsin foydalanuvchilari |
| **Stripe** | Xorijiy | Xorijiy talabalar (USD/EUR) |
| **Bank o'tkazma** | Manual | Yuridik shaxslar |

### 2. Kontrakt boshqaruvi

- Kontrakt PDF avtomatik yaratish
- Kontrakt raqami: `KT-{YIL}-{TARTIB_RAQAM}`
- Kontrakt summa (yo'nalish bo'yicha)
- Kontrakt davomiyligi (ta'lim yili)
- Bo'lib-bo'lib to'lash imkoniyati (3-4 qism)
- ERI bilan imzolash
- Yangilash (har yil)

### 3. To'lov rejasi

Talaba quyidagicha to'lay oladi:
- **Bir martalik** — to'liq summa
- **Yarim yarim** — 50% sentyabrda, 50% fevralda
- **Choraklik** — 4 marta
- **Oylik** — 9 oy davomida (ixtiyoriy)

### 4. Qarz boshqaruvi

- Joriy balans hisoblash
- Tushgan to'lovlar tarixi
- Bo'lib to'lash sanalari va miqdorlari
- Kechiktirilgan to'lovlar
- Kechiktirish jazo (% har kunlik, ixtiyoriy)
- SMS / email reminderlar

### 5. Talaba kabineti

- Joriy balans
- Kontrakt (PDF download)
- To'lov tarixi
- Keyingi to'lov sanasi va summa
- "To'lash" tugmasi
- Receipt (chek) yaratish

### 6. Admin paneli

- Barcha to'lovlar ro'yxati
- Filter: status, sana, OTM, mutaxassislik
- Manual to'lov qo'shish (bank o'tkazma)
- Refund (qaytarish)
- Statistika va hisobotlar

### 7. Webhook qabul qilish

- Click webhook (prepare/complete)
- Payme webhook (CheckPerformTransaction, CreateTransaction, PerformTransaction, CancelTransaction)
- Imzo tekshiruvi (HMAC)
- Idempotent qayta ishlash

### 8. Hisob-kitob

- 1C va boshqa buxgalteriya tizimlari bilan integratsiya
- Eksport: Excel, CSV, JSON
- Soliq hisobotlari

## API Endpoints

```
# Kontraktlar
GET    /api/v1/contracts                      # ro'yxat
POST   /api/v1/contracts                      # yaratish
GET    /api/v1/contracts/{id}
GET    /api/v1/contracts/{id}/pdf             # PDF yuklab olish
POST   /api/v1/contracts/{id}/sign            # ERI imzolash
POST   /api/v1/contracts/{id}/cancel          # bekor qilish

# To'lovlar
GET    /api/v1/payments                       # ro'yxat
GET    /api/v1/payments/{id}
POST   /api/v1/payments/initiate              # to'lovni boshlash (URL qaytaradi)
POST   /api/v1/payments/manual                # manual qo'shish (admin)
GET    /api/v1/payments/{id}/receipt          # chek

# Talaba
GET    /api/v1/students/me/balance            # mening balansim
GET    /api/v1/students/me/payments           # mening to'lovlarim
GET    /api/v1/students/me/contract           # mening kontraktim
GET    /api/v1/students/me/payment-schedule   # to'lov rejasi

# Webhook'lar
POST   /api/v1/webhooks/click
POST   /api/v1/webhooks/payme
POST   /api/v1/webhooks/apelsin

# Hisobot
GET    /api/v1/payments/reports/summary
GET    /api/v1/payments/export.xlsx
```

## Database modellari

```sql
-- Kontrakt
CREATE TABLE contracts (
    id BIGSERIAL PRIMARY KEY,
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    
    student_id BIGINT REFERENCES students(id),
    organization_id BIGINT REFERENCES organizations(id),
    specialty_id BIGINT REFERENCES specialties(id),
    
    academic_year VARCHAR(20) NOT NULL,            -- '2026-2027'
    
    -- Summa
    total_amount NUMERIC(12, 2) NOT NULL,
    paid_amount NUMERIC(12, 2) DEFAULT 0,
    balance NUMERIC(12, 2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,
    
    currency VARCHAR(3) DEFAULT 'UZS',
    
    -- Davomiyligi
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',            -- 'draft', 'active', 'fulfilled', 'cancelled'
    
    -- PDF
    pdf_url TEXT,
    signed_pdf_url TEXT,
    signed_at TIMESTAMP,
    signed_method VARCHAR(20),                     -- 'eri', 'manual'
    
    -- Bo'lib to'lash
    payment_plan VARCHAR(20) DEFAULT 'one_time',   -- 'one_time', 'half', 'quarterly', 'monthly'
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- To'lov rejasi
CREATE TABLE payment_schedules (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT REFERENCES contracts(id) ON DELETE CASCADE,
    installment_number INT NOT NULL,
    due_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    paid_amount NUMERIC(12, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',          -- 'pending', 'paid', 'overdue'
    paid_at TIMESTAMP,
    
    UNIQUE(contract_id, installment_number)
);

-- To'lov
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    
    contract_id BIGINT REFERENCES contracts(id),
    student_id BIGINT REFERENCES students(id),
    schedule_id BIGINT REFERENCES payment_schedules(id),
    
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'UZS',
    
    -- Provayder
    provider VARCHAR(20) NOT NULL,                 -- 'click', 'payme', 'apelsin', 'manual', 'bank'
    provider_transaction_id VARCHAR(200),
    provider_payment_url TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',          -- 'pending', 'processing', 'completed', 'failed', 'refunded'
    
    -- Sanalari
    initiated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    -- Refund
    refunded_amount NUMERIC(12, 2) DEFAULT 0,
    refunded_at TIMESTAMP,
    refund_reason TEXT,
    
    -- Metadata
    metadata JSONB,
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_student ON payments(student_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider_tx ON payments(provider, provider_transaction_id);

-- Webhook eventlar (audit)
CREATE TABLE payment_webhook_events (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(20) NOT NULL,
    event_type VARCHAR(50),
    payment_id BIGINT REFERENCES payments(id),
    payload JSONB,
    headers JSONB,
    received_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    error TEXT
);
```

## Click integratsiyasi

```python
# app/integrations/click/client.py
import hashlib
import time
from app.core.config import settings

class ClickClient:
    def __init__(self):
        self.merchant_id = settings.CLICK_MERCHANT_ID
        self.service_id = settings.CLICK_SERVICE_ID
        self.secret_key = settings.CLICK_SECRET_KEY
    
    def create_invoice_url(self, payment_id: int, amount: int) -> str:
        """Click to'lov sahifasiga URL yaratish"""
        return (
            f"https://my.click.uz/services/pay"
            f"?service_id={self.service_id}"
            f"&merchant_id={self.merchant_id}"
            f"&amount={amount}"
            f"&transaction_param={payment_id}"
            f"&return_url={settings.FRONTEND_URL}/payments/return"
        )
    
    def verify_signature(
        self, click_trans_id: str, service_id: str,
        merchant_trans_id: str, amount: str, action: str,
        sign_time: str, sign_string: str,
    ) -> bool:
        """Webhook imzosini tekshirish"""
        signature = hashlib.md5(
            f"{click_trans_id}{service_id}{self.secret_key}{merchant_trans_id}{amount}{action}{sign_time}".encode()
        ).hexdigest()
        return signature == sign_string
```

## Click webhook handler

```python
# app/api/v1/webhooks.py

@router.post("/click")
async def click_webhook(request: Request):
    form = await request.form()
    
    # Parametrlar
    click_trans_id = form.get("click_trans_id")
    service_id = form.get("service_id")
    merchant_trans_id = form.get("merchant_trans_id")  # bizning payment_id
    amount = form.get("amount")
    action = int(form.get("action"))                    # 0=Prepare, 1=Complete
    error = int(form.get("error"))
    sign_time = form.get("sign_time")
    sign_string = form.get("sign_string")
    
    # Imzo tekshiruvi
    client = ClickClient()
    if not client.verify_signature(
        click_trans_id, service_id, merchant_trans_id, amount, action, sign_time, sign_string
    ):
        return {"error": -1, "error_note": "Sign check failed"}
    
    # Payment'ni topish
    payment = await get_payment(int(merchant_trans_id))
    if not payment:
        return {"error": -5, "error_note": "Payment not found"}
    
    # Action handling
    if action == 0:  # Prepare
        if payment.status != "pending":
            return {"error": -4, "error_note": "Already paid"}
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": payment.id,
            "error": 0,
            "error_note": "Success",
        }
    
    elif action == 1:  # Complete
        if error == 0:
            await complete_payment(payment.id, click_trans_id)
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": payment.id,
                "error": 0,
                "error_note": "Success",
            }
        else:
            await fail_payment(payment.id, str(error))
            return {"error": error, "error_note": "Failed"}
```

## Payme integratsiyasi (Subscribe API)

Payme JSON-RPC orqali ishlaydi:

```python
# app/integrations/payme/handler.py

class PaymeHandler:
    """Payme Subscribe API handler"""
    
    METHODS = {
        "CheckPerformTransaction": "_check_perform",
        "CreateTransaction": "_create_transaction",
        "PerformTransaction": "_perform_transaction",
        "CancelTransaction": "_cancel_transaction",
        "CheckTransaction": "_check_transaction",
        "GetStatement": "_get_statement",
    }
    
    async def handle(self, body: dict) -> dict:
        method = body.get("method")
        params = body.get("params", {})
        
        if method not in self.METHODS:
            return self._error(-32601, "Method not found")
        
        handler = getattr(self, self.METHODS[method])
        return await handler(params)
    
    async def _check_perform(self, params: dict):
        # account['payment_id'] orqali to'lovni tekshirish
        payment_id = params["account"]["payment_id"]
        amount = params["amount"]  # tiyin'da
        
        payment = await get_payment(payment_id)
        if not payment:
            return self._error(-31050, "Payment not found")
        
        if payment.amount * 100 != amount:
            return self._error(-31001, "Wrong amount")
        
        return {"result": {"allow": True}}
    
    async def _create_transaction(self, params: dict):
        # Tranzaksiya yaratish
        # ...
```

## PDF kontrakt generatsiya

```python
# app/utils/pdf.py
from weasyprint import HTML
from jinja2 import Template

CONTRACT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Times New Roman'; font-size: 12pt; }
        .header { text-align: center; }
        .signature { margin-top: 50px; display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="header">
        <h2>TA'LIM XIZMATLARINI KO'RSATISH SHARTNOMASI</h2>
        <p>№ {{ contract.contract_number }}</p>
        <p>{{ today }}</p>
    </div>
    
    <p><strong>Tomonlar:</strong></p>
    <p>{{ org.name }} (bundan keyin "Bajaruvchi") va</p>
    <p>{{ student.full_name }}, PINFL: {{ student.pinfl }} (bundan keyin "Talaba")</p>
    
    <h3>1. Shartnoma predmeti</h3>
    <p>Bajaruvchi {{ specialty.name }} yo'nalishi bo'yicha masofaviy ta'lim xizmatlarini ko'rsatish ...</p>
    
    <h3>2. Shartnoma summasi</h3>
    <p>{{ contract.total_amount }} so'm</p>
    
    <div class="signature">
        <div>Bajaruvchi: ________________</div>
        <div>Talaba: ________________</div>
    </div>
</body>
</html>
"""

async def generate_contract_pdf(contract_id: int) -> str:
    contract = await get_contract(contract_id)
    
    html = Template(CONTRACT_TEMPLATE).render(
        contract=contract,
        student=contract.student,
        org=contract.organization,
        specialty=contract.specialty,
        today=datetime.utcnow().strftime("%d.%m.%Y"),
    )
    
    pdf_bytes = HTML(string=html).write_pdf()
    
    # MinIO'ga yuklash
    url = await upload_to_storage(pdf_bytes, f"contracts/{contract.contract_number}.pdf")
    
    contract.pdf_url = url
    await save(contract)
    
    return url
```

## Acceptance kriteriyalar

- [ ] Kontrakt PDF generatsiya
- [ ] ERI imzo
- [ ] Click integratsiyasi
- [ ] Payme integratsiyasi
- [ ] Apelsin integratsiyasi (ixtiyoriy)
- [ ] Webhook xavfsizligi (HMAC)
- [ ] Bo'lib to'lash rejasi
- [ ] Talaba kabineti
- [ ] Admin paneli
- [ ] Refund flowi
- [ ] SMS/email reminderlar
- [ ] Hisobotlar (Excel eksport)
- [ ] Test coverage ≥ 85%
