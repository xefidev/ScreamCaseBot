# ScreamCase - Security Architecture Diagram

## Request Flow Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                            │
│  CasePreview.jsx / ProfilePage.jsx                              │
│                                                                  │
│  Layer 1: Input Validation                                      │
│  - Check userId, caseId, amount format                          │
│  - Prevent negative values                                      │
│  - Validate promo code format                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │ POST /api/open_case
                     │ POST /api/claim_promo
                     │ POST /api/ton_success
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API GATEWAY (src/api.js)                       │
│                                                                  │
│  Layer 2: Request Formation & Error Handling                    │
│  - Format JSON payload                                          │
│  - Handle network errors                                        │
│  - Parse response & extract errors                              │
│  - Show user-friendly alerts                                    │
│  - Structured error throwing                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP Request
                     │ (SSL/TLS Encrypted)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND API (bot.py - aiohttp)                      │
│                                                                  │
│  Layer 3: Request Validation                                    │
│  - Verify request format                                        │
│  - Check required fields                                        │
│  - Validate data types                                          │
│  - Return 400 if invalid                                        │
└────────────────────┬────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│            SECURITY CHECK LAYERS (bot.py)                        │
│                                                                  │
│  Layer 4: Authorization Check                                   │
│  - Verify user_id parameter                                     │
│  - For admin endpoints: verify admin_id in ADMIN_IDS            │
│  - Return 403 if unauthorized                                   │
│                                                                  │
│  Layer 5: Resource Validation                                   │
│  - For case_id: verify in CASES_PRICES config                   │
│  - For promo code: check exists in DB                           │
│  - For TON tx: check format & amount > 0                        │
│  - Return 400/404 if invalid                                    │
│                                                                  │
│  Layer 6: Business Logic Validation                             │
│  - For case open: check user balance >= price                   │
│  - For daily: check 24h cooldown                                │
│  - For promo: check active, expiry, donation requirement        │
│  - For TON: check duplicate tx hash                             │
│  - Return 403 if check fails                                    │
└────────────────────┬────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           DATABASE UPDATE LAYER (bot.py)                         │
│                                                                  │
│  Layer 7: Atomic Transaction                                    │
│  with sqlite3.connect('database.db') as conn:                   │
│    1. SELECT user balance (verify balance >= price)             │
│    2. INSERT transaction record (immutable log)                 │
│    3. UPDATE user balance (deduct/add stars)                    │
│    4. conn.commit() (all or nothing)                            │
│                                                                  │
│  Layer 8: Deferred Response                                     │
│  - ONLY after DB commit                                         │
│  - Return 200 {"success": true}                                 │
│                                                                  │
│  If ANY layer fails: Return error code, NO DB update            │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP Response
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              ERROR HANDLING (Frontend)                            │
│                                                                  │
│  Layer 9: Response Processing                                   │
│  - Check response.status                                        │
│  - If error: handleApiError()                                   │
│  - Format message: formatErrorMessage()                         │
│  - Show alert: Telegram.WebApp.showAlert()                      │
│  - STOP animation/transactions                                  │
│  - Propagate error for component handling                       │
│                                                                  │
│  Layer 10: Component State Recovery                             │
│  - Stop animations (setIsSpinning = false)                      │
│  - Hide confetti & result modals                                │
│  - Reset form inputs                                            │
│  - Ready for retry                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Price Authority Flow

```
ATTACK: Client sends custom price

  Frontend (attacker)
     ↓
  POST /api/open_case
  { user_id: 123456, case_id: 3, price: 1 }
     ↓ ❌ REJECTED
  Backend (bot.py)
     ↓
  # CRITICAL: Fetch price from config, IGNORE request
  price = CASES_PRICES.get(3)  # = 667
     ↓
  # Price NOW 667, attacker's price ignored
  if user_balance < 667:
      return 403
     ↓
  # If balance OK, deduct 667 (CORRECT)
  conn.execute("UPDATE users SET stars = stars - 667")
```

---

## Balance Deduction Safety

```
SCENARIO: System crash during case open

  Initial State:
  user balance = 1000

  Request: Open case (cost 667)

  BACKEND SEQUENCE:
  1. SELECT balance: 1000 ✓
  2. Check: 1000 >= 667 ✓
  3. UPDATE users SET stars = 1000 - 667
  4. INSERT payments record
  5. conn.commit() ← ATOMIC POINT
  6. Return {"success": true}

  CRASH SCENARIOS:
  
  Crash at Step 1-2:
  - Balance NOT changed
  - No transaction record
  - User can retry safely
  
  Crash at Step 3:
  - Update not committed
  - Balance NOT changed
  - User can retry safely
  
  Crash after Step 5:
  - Update COMMITTED to DB
  - Balance = 333
  - Transaction logged
  - User WILL see result (correct)
  
  RESULT: IMPOSSIBLE to have partial update
```

---

## Promo Code Validation Layers

```
User enters code: "PROMOTION"

  Layer 1: Format Check
  ├─ Is code empty? → NO
  ├─ Is code string? → YES
  ├─ Length 3-50? → YES (11 chars) ✓
  
  Layer 2: Existence Check
  ├─ SELECT FROM promocodes WHERE code = "PROMOTION"
  ├─ Code found? → YES ✓
  └─ Code data: {reward: 500, active: 1, expires_at: "2026-05-20"}
  
  Layer 3: Active Check
  ├─ Is active = 1? → YES ✓
  
  Layer 4: Expiry Check
  ├─ Current time: 2026-05-12
  ├─ Expires at: 2026-05-20
  ├─ Is now < expires? → YES ✓
  
  Layer 5: Donation Requirement Check
  ├─ min_donation_24h: 100
  ├─ User donated in last 24h: 250
  ├─ Is 250 >= 100? → YES ✓
  
  ALL CHECKS PASS ✓
  ├─ Add 500 stars to user
  ├─ Log transaction
  ├─ Return {"success": true, "reward": 500}

FAILURE AT ANY LAYER:
  └─ Return error immediately
  └─ NO reward granted
  └─ Show specific error message
```

---

## TON Transaction Duplicate Prevention

```
First Payment: 1.5 TON

  Request:
  POST /api/ton_success
  { user_id: 123, amount: 1.5, tx_id: "EQCxE6..." }
  
  Backend:
  1. Hash tx_id → SHA256("EQCxE6...") = "abc123..."
  2. Check: SELECT FROM ton_transactions WHERE tx_id = "abc123..."
     → No result
  3. INSERT into ton_transactions: ("abc123...", 123, 1.5)
  4. UPDATE users: stars += 150
  5. conn.commit()
  6. Response: {"success": true, "stars_added": 150}

Database State:
ton_transactions: [
  {tx_id: "abc123...", user_id: 123, amount: 1.5}
]
users: [
  {user_id: 123, stars: 150}  (was 0)
]

---

Second Payment (DUPLICATE tx_id):

  Request: Same tx_id "EQCxE6..."
  
  Backend:
  1. Hash tx_id → SHA256("EQCxE6...") = "abc123..."
  2. Check: SELECT FROM ton_transactions WHERE tx_id = "abc123..."
     → FOUND! Record exists
  3. Return error immediately (400)
     {"error": "transaction_already_processed"}
  4. NO database update
  5. User stars remain 150 (correct)

Result:
✓ Impossible to double-spend
✓ Transaction stored immutably
✓ Duplicate detected by hash
```

---

## Error Response Codes

```
Request Analysis Flow:

Request arrives
  ↓
Is JSON valid?
  ├─ NO → 400 Bad Request
  └─ YES ↓
Is required field missing?
  ├─ YES → 400 Bad Request
  └─ NO ↓
Is user_id valid type?
  ├─ NO → 400 Bad Request
  └─ YES ↓
Is user_id in database?
  ├─ NO → 404 Not Found (for GET endpoints)
  └─ YES ↓
Is user authorized?
  ├─ NO → 403 Forbidden
  └─ YES ↓
Is resource valid (case_id, promo code)?
  ├─ NO → 400/404
  └─ YES ↓
Is business logic satisfied?
  (balance, cooldown, expiry, requirements)
  ├─ NO → 403 Forbidden
  └─ YES ↓
Execute DB transaction
  ↓
200 OK (Success)
```

---

## Frontend Animation Safety

```
User clicks "OPEN CASE"

  handleOpen()
  ├─ Is spinning? → YES → RETURN (prevent double-spin)
  ├─ Can open? → NO → RETURN
  └─ Continue ↓
  
  setIsSpinning(true)  ← LOCK UI IMMEDIATELY
  
  Try:
  ├─ Call openCase() API
  │  ├─ Response error → api.js shows alert
  │  └─ Catch block ↓
  ├─ setIsSpinning(false)  ← UNLOCK
  ├─ setHasSpun(false)
  ├─ setShowConfetti(false)
  ├─ setShowResult(false)
  └─ Done

Result:
✓ User sees error alert
✓ Animation never started (isSpinning = true → false)
✓ No confetti
✓ No stuck animation
✓ UI ready for retry
```

---

## Security Logging

```
AUDIT TRAIL EXAMPLE:

[INFO] User 12345 registered: John Doe
[INFO] User 12345 opened case 3, deducted 667 stars
[WARNING] User 12345 insufficient funds for case 3 (req: 667, has: 100)
[INFO] User 12345 claimed daily case
[INFO] User 12345 claimed promo SUMMER2026 for 500 stars
[INFO] Admin 7782281997 created promo: PROMOTION (expires: 2026-05-20)
[INFO] TON payment: User 12345, 1.5 TON = 150 stars, TX: abc123...
[WARNING] Duplicate TON transaction detected: abc123...
[ERROR] Database error in api_ton_success: [error details]

All logged with timestamps and severity levels
```

---

**CONCLUSION**: 10-layer security architecture ensures:
- ✅ No price manipulation
- ✅ No balance exploits
- ✅ No duplicate payments
- ✅ No invalid claims
- ✅ No animation glitches
- ✅ Clear error messages
- ✅ Complete audit trail
