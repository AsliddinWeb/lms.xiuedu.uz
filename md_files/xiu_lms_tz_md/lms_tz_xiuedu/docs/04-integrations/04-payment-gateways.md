# 04. Toʻlov Tizimlari (Click, Payme, Apelsin)

## Click

### Texnik tafsilotlar
- **Protokol:** Click Merchant API + SHOP API
- **URL:** `https://my.click.uz/services/pay`
- **Webhook:** `Prepare` (action=0) va `Complete` (action=1)
- **Imzo:** MD5 hash

### Kerakli ma'lumotlar
```env
CLICK_MERCHANT_ID=xxx
CLICK_SERVICE_ID=xxx
CLICK_SECRET_KEY=xxx
CLICK_USER_ID=xxx
```

### To'lov flow
1. LMS — Payment record yaratadi (status=`pending`)
2. LMS — Click pay URL generatsiya qiladi
3. Talaba Click sahifasiga o'tadi → karta ma'lumotlari → tasdiqlash
4. Click webhook (action=0, Prepare) → biz `merchant_prepare_id` qaytaramiz
5. Click webhook (action=1, Complete) → biz to'lovni `completed` qilamiz
6. Talabaga chek

Implementatsiya: [03-modules/10-payments.md](../03-modules/10-payments.md)

## Payme

### Texnik tafsilotlar
- **Protokol:** Subscribe API (JSON-RPC 2.0)
- **URL:** `https://checkout.paycom.uz`
- **Webhook:** Bizga (Merchant API)

### Kerakli ma'lumotlar
```env
PAYME_MERCHANT_ID=xxx
PAYME_KEY=xxx                    # test
PAYME_KEY_PROD=xxx               # production
PAYME_LOGIN=Paycom               # webhook auth login
```

### Payme metodlari (Merchant API)

Bizning endpoint Payme'dan JSON-RPC requestlarni qabul qiladi:

| Method | Tavsifi |
|--------|---------|
| `CheckPerformTransaction` | To'lov mumkinligini tekshirish |
| `CreateTransaction` | Tranzaksiya yaratish |
| `PerformTransaction` | Tranzaksiyani tasdiqlash |
| `CancelTransaction` | Bekor qilish |
| `CheckTransaction` | Tranzaksiya holati |
| `GetStatement` | Davriy hisobot |

### Implementatsiya

```python
# app/integrations/payme/handler.py
from fastapi import APIRouter, Depends, Header, HTTPException
import base64

router = APIRouter()

PAYME_ERRORS = {
    "transaction_not_found": -31003,
    "wrong_amount": -31001,
    "order_completed": -31051,
    "order_not_found": -31050,
    "internal_error": -32400,
    "method_not_found": -32601,
    "auth_error": -32504,
}


@router.post("/payme")
async def payme_webhook(
    body: dict,
    authorization: str = Header(...),
):
    # Auth tekshiruvi
    expected = base64.b64encode(
        f"Paycom:{settings.PAYME_KEY}".encode()
    ).decode()
    
    if authorization != f"Basic {expected}":
        return {
            "error": {
                "code": PAYME_ERRORS["auth_error"],
                "message": "Auth failed"
            },
            "id": body.get("id"),
        }
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    handler = PaymeHandler()
    
    try:
        if method == "CheckPerformTransaction":
            result = await handler.check_perform(params)
        elif method == "CreateTransaction":
            result = await handler.create_transaction(params)
        elif method == "PerformTransaction":
            result = await handler.perform_transaction(params)
        elif method == "CancelTransaction":
            result = await handler.cancel_transaction(params)
        elif method == "CheckTransaction":
            result = await handler.check_transaction(params)
        elif method == "GetStatement":
            result = await handler.get_statement(params)
        else:
            return {
                "error": {
                    "code": PAYME_ERRORS["method_not_found"],
                    "message": "Method not found",
                },
                "id": request_id,
            }
        
        return {"result": result, "id": request_id}
        
    except PaymeError as e:
        return {
            "error": {"code": e.code, "message": e.message},
            "id": request_id,
        }


class PaymeHandler:
    async def check_perform(self, params: dict):
        account = params["account"]
        amount = params["amount"]  # tiyin (so'mning 1/100)
        
        payment_id = account.get("payment_id")
        if not payment_id:
            raise PaymeError(-31050, "Payment ID required")
        
        payment = await get_payment(int(payment_id))
        if not payment:
            raise PaymeError(-31050, "Payment not found")
        
        if payment.status != "pending":
            raise PaymeError(-31051, "Already paid or cancelled")
        
        if int(payment.amount * 100) != amount:
            raise PaymeError(-31001, "Wrong amount")
        
        return {"allow": True}
    
    async def create_transaction(self, params: dict):
        tx_id = params["id"]              # Payme transaction ID
        time = params["time"]              # ms
        amount = params["amount"]
        account = params["account"]
        
        payment_id = int(account["payment_id"])
        
        # Avval mavjudligini tekshirish (idempotent)
        existing = await find_payme_transaction(tx_id)
        if existing:
            return {
                "create_time": existing.create_time,
                "transaction": str(existing.id),
                "state": existing.state,
            }
        
        # Validate
        await self.check_perform(params)
        
        # Create
        transaction = await create_payme_transaction(
            payme_id=tx_id,
            payment_id=payment_id,
            amount=amount,
            create_time=time,
            state=1,  # 1 = created
        )
        
        return {
            "create_time": time,
            "transaction": str(transaction.id),
            "state": 1,
        }
    
    async def perform_transaction(self, params: dict):
        tx_id = params["id"]
        
        transaction = await find_payme_transaction(tx_id)
        if not transaction:
            raise PaymeError(-31003, "Transaction not found")
        
        if transaction.state == 1:
            # Tasdiqlash
            transaction.state = 2  # 2 = performed
            transaction.perform_time = int(time.time() * 1000)
            await save(transaction)
            
            # To'lovni complete qilish
            await complete_payment(
                transaction.payment_id,
                provider="payme",
                provider_tx_id=tx_id,
            )
        
        return {
            "transaction": str(transaction.id),
            "perform_time": transaction.perform_time,
            "state": transaction.state,
        }
    
    async def cancel_transaction(self, params: dict):
        tx_id = params["id"]
        reason = params["reason"]
        
        transaction = await find_payme_transaction(tx_id)
        if not transaction:
            raise PaymeError(-31003, "Transaction not found")
        
        if transaction.state == 1:
            transaction.state = -1  # -1 = cancelled
        elif transaction.state == 2:
            transaction.state = -2  # -2 = cancelled after perform
            # Refund
            await refund_payment(transaction.payment_id)
        
        transaction.cancel_time = int(time.time() * 1000)
        transaction.reason = reason
        await save(transaction)
        
        return {
            "transaction": str(transaction.id),
            "cancel_time": transaction.cancel_time,
            "state": transaction.state,
        }
    
    async def check_transaction(self, params: dict):
        tx_id = params["id"]
        
        transaction = await find_payme_transaction(tx_id)
        if not transaction:
            raise PaymeError(-31003, "Transaction not found")
        
        return {
            "create_time": transaction.create_time,
            "perform_time": transaction.perform_time or 0,
            "cancel_time": transaction.cancel_time or 0,
            "transaction": str(transaction.id),
            "state": transaction.state,
            "reason": transaction.reason,
        }


class PaymeError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
```

### Payme'da to'lov boshlash (frontend)

```typescript
// frontend
function payWithPayme(paymentId: number, amount: number) {
  // Base64 encoded: m={merchant_id};ac.payment_id={payment_id};a={amount}
  const params = `m=${MERCHANT_ID};ac.payment_id=${paymentId};a=${amount * 100}`
  const encoded = btoa(params)
  
  window.location.href = `https://checkout.paycom.uz/${encoded}`
}
```

### Payme database

```sql
CREATE TABLE payme_transactions (
    id BIGSERIAL PRIMARY KEY,
    payme_id VARCHAR(100) UNIQUE NOT NULL,
    payment_id BIGINT REFERENCES payments(id),
    amount BIGINT NOT NULL,                    -- tiyin
    state INT NOT NULL,                        -- 1, 2, -1, -2
    reason INT,
    create_time BIGINT,
    perform_time BIGINT,
    cancel_time BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payme_payment ON payme_transactions(payment_id);
```

## Apelsin

### Texnik tafsilotlar
- **Protokol:** Apelsin Merchant API
- **URL:** `https://chk.apl.uz` (asosiy), `https://chk-test.apl.uz` (test)
- **Imzo:** HMAC-SHA256

### Endpoint'lar
- **Bizdan Apelsinga:** Invoice yaratish
- **Apelsindan bizga:** Status webhook

### Implementatsiya

```python
# app/integrations/apelsin/client.py

class ApelsinClient:
    BASE_URL = settings.APELSIN_BASE_URL
    
    def __init__(self):
        self.merchant_id = settings.APELSIN_MERCHANT_ID
        self.secret = settings.APELSIN_SECRET
    
    async def create_invoice(self, payment_id: int, amount: int) -> dict:
        body = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "external_id": str(payment_id),
            "callback_url": f"{settings.API_URL}/api/v1/webhooks/apelsin",
            "return_url": f"{settings.FRONTEND_URL}/payments/return",
        }
        
        # Imzo
        signature = self._sign(body)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/api/invoice/create",
                json=body,
                headers={"X-Signature": signature},
            )
            return response.json()
    
    def _sign(self, body: dict) -> str:
        message = json.dumps(body, sort_keys=True)
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
```

## Acceptance kriteriyalar

- [ ] Click Prepare/Complete webhook
- [ ] Click imzo tekshiruvi
- [ ] Payme barcha 6 metod
- [ ] Payme idempotent transactionlar
- [ ] Apelsin invoice yaratish va webhook
- [ ] Refund jarayoni
- [ ] Audit log barcha tranzaksiyalar
- [ ] Retry / DLQ failed webhooks uchun
- [ ] Test coverage ≥ 85%
