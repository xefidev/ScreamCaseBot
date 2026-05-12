# ScreamCase - Security Testing Guide

## Quick Test Matrix

### 1. INSUFFICIENT FUNDS TEST
```
Scenario: User has 100 ⭐, tries to open case costing 500 ⭐

Request:
POST /api/open_case
{
  "user_id": 123456,
  "case_id": 3,
  "code": null
}

Expected Response (403):
{
  "error": "insufficient_funds",
  "required": 500,
  "current": 100,
  "status": 403
}

Verification:
✓ User's balance remains 100 (no deduction)
✓ showAlert triggered with "❌ Недостаточно средств"
✓ Animation stopped
```

### 2. DAILY COOLDOWN TEST
```
Scenario: User tries to claim daily case twice

First Claim:
POST /api/open_case
{
  "user_id": 123456,
  "case_id": 2
}

Response (200):
{"success": true}
✓ last_daily updated in DB

Second Claim (same day):
POST /api/open_case
{
  "user_id": 123456,
  "case_id": 2
}

Expected Response (403):
{
  "error": "daily_cooldown_active",
  "wait_seconds": 83400,  // ~23h remaining
  "status": 403
}

Verification:
✓ Wait time calculated correctly
✓ Alert shows hours remaining
✓ No duplicate claim allowed
```

### 3. INVALID PROMO CODE TEST
```
Scenario: User tries to use fake promo code

Request:
POST /api/claim_promo
{
  "user_id": 123456,
  "code": "FAKECODE123"
}

Expected Response (404):
{
  "error": "invalid_code",
  "status": 404
}

Verification:
✓ No reward granted
✓ showAlert: "❌ Неверный промокод"
✓ Balance unchanged
```

### 4. EXPIRED PROMO CODE TEST
```
Scenario: Code exists but is expired

Promo in DB:
{
  "code": "OLDCODE",
  "reward": 100,
  "active": 1,
  "expires_at": "2026-05-10 00:00:00"  // Yesterday
}

Request:
POST /api/claim_promo
{
  "user_id": 123456,
  "code": "OLDCODE"
}

Expected Response (403):
{
  "error": "code_expired",
  "status": 403
}

Verification:
✓ Alert: "❌ Промокод истёк"
✓ Expired check happens before reward check
```

### 5. MINIMUM DONATION REQUIREMENT TEST
```
Scenario: Promo requires $5 donation in last 24h, user has $0

Promo in DB:
{
  "code": "DONATECODE",
  "reward": 500,
  "min_donation_24h": 500,  // Requires 500 stars in last 24h
  "active": 1
}

User's donations (last 24h): 100 stars

Request:
POST /api/claim_promo
{
  "user_id": 123456,
  "code": "DONATECODE"
}

Expected Response (403):
{
  "error": "minimum_donation_required",
  "required": 500,
  "current": 100,
  "status": 403
}

Verification:
✓ Donation amount checked
✓ Only counts positive payments (amount > 0)
✓ Only checks last 24 hours
```

### 6. DUPLICATE TON TRANSACTION TEST
```
Scenario: Same TON transaction processed twice

First Transaction:
POST /api/ton_success
{
  "user_id": 123456,
  "amount": 1.5,
  "tx_id": "EQCxE...hash...xyz"
}

Response (200):
{
  "success": true,
  "stars_added": 150
}

Verification:
✓ 150 stars added to user
✓ Transaction hash stored in ton_transactions table

Second Transaction (same hash):
POST /api/ton_success
{
  "user_id": 123456,
  "amount": 1.5,
  "tx_id": "EQCxE...hash...xyz"
}

Expected Response (400):
{
  "error": "transaction_already_processed",
  "status": 400
}

Verification:
✓ NO additional stars added
✓ User balance remains unchanged
✓ Alert: "❌ Эта транзакция уже обработана"
```

### 7. PRICE OVERRIDE TEST
```
Scenario: Client tries to send custom price

Request (ATTACKED):
POST /api/open_case
{
  "user_id": 123456,
  "case_id": 3,
  "price": 1  // Attacker tries to set price to 1 star!
}

Backend Behavior:
✓ Ignores "price" field from request
✓ Fetches price from CASES_PRICES config
✓ Case 3 = 667 stars (from config)

Expected Deduction:
667 stars (correct price, not 1)

Verification:
✓ Attack price rejected
✓ Config price used always
✓ No way to override server price
```

### 8. COMMAND HANDLER TEST
```
Scenario: Invalid command sent to bot

Message: /invalidcommand

Expected Response:
"❌ Неизвестная команда. Введите `/help` для справки."

Verification:
✓ Bot doesn't crash
✓ Unknown command handler triggered
✓ User gets helpful message
```

### 9. ADMIN AUTHORIZATION TEST
```
Scenario: Non-admin tries to create promo

Request:
POST /api/admin/create_promo
{
  "admin_id": 999999999,  // Not in ADMIN_IDS
  "code": "ANYCODE",
  "reward": 100,
  "days": 7
}

Expected Response (403):
{
  "error": "unauthorized",
  "status": 403
}

Verification:
✓ Only ADMIN_IDS can create promos
✓ ADMIN_IDS: [7782281997, 5396975347]
✓ Non-admin rejected with 403
```

### 10. BALANCE CHECK BEFORE DEDUCTION TEST
```
Scenario: Verify balance is checked BEFORE DB update

Database State Before:
users table: { user_id: 123456, stars: 100 }
payments table: (clean, no recent records)

Request:
POST /api/open_case
{
  "user_id": 123456,
  "case_id": 3  // costs 667
}

Expected State After:
users table: { user_id: 123456, stars: 100 }  // UNCHANGED
payments table: (no new record added)

Response (403):
{
  "error": "insufficient_funds",
  "required": 667,
  "current": 100
}

Verification:
✓ Database NOT modified
✓ No partial state
✓ Safe to retry
```

## Frontend Error Scenarios

### Animation Stop Test
```
State: CasePreview spinning animation in progress
Action: Server returns 403 error
Expected:
✓ isSpinning set to false immediately
✓ Animation stops
✓ Confetti hidden
✓ Result modal hidden
✓ showAlert appears

Code Flow:
  handleOpen()
    ↓ setIsSpinning(true)
    ↓ openCase() → API error
    ↓ catch block
      ↓ setIsSpinning(false) ✅
      ↓ setShowConfetti(false) ✅
      ↓ setShowResult(false) ✅
```

## Logging Verification

Check console for:
```
[INFO] User 123456 opened case 3, deducted 667 stars
[WARNING] User 123456 attempted to open case with insufficient funds
[INFO] User 123456 claimed promo code VALID01
[ERROR] User 123456 attempted invalid promo: FAKECODE
[WARNING] Duplicate TON transaction detected: sha256hash...
```

## Database Inspection

```sql
-- Check balance after case open
SELECT user_id, stars FROM users WHERE user_id = 123456;

-- Check daily claim cooldown
SELECT user_id, last_daily FROM users WHERE user_id = 123456;

-- Check promo codes
SELECT code, reward, active, expires_at FROM promocodes;

-- Check TON transactions
SELECT tx_id, user_id, amount, date FROM ton_transactions;

-- Check payment history
SELECT user_id, amount, date FROM payments WHERE user_id = 123456;
```

---

**All tests should PASS for security clearance.**
