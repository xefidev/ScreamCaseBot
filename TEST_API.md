# API Testing Guide - ScreamCase

## Проверка работы эндпоинтов

### 1. Проверка баланса (GET /api/balance)

```bash
# Тест с Query параметром (work in dev mode)
curl -X GET "https://screamcasebot.onrender.com/api/balance?user_id=7782281997" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
{
  "stars": 100000,
  "tickets": 0,
  "donor": 0,
  "spent": 0,
  "promo_opened": 0
}
```

### 2. Проверка создания инвойса (POST /api/create_invoice)

```bash
# Тест с user_id в body
curl -X POST "https://screamcasebot.onrender.com/api/create_invoice" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 7782281997,
    "amount": 10,
    "payment_type": "ton",
    "initData": ""
  }'

# Ожидаемый ответ:
{
  "wallet": "UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp",
  "comment": "SC_7782281997_ABC123",
  "payload_boc": "...",
  "rate": 100
}
```

### 3. Проверка открытия кейса (POST /api/open_case)

```bash
# Тест открытия кейса
curl -X POST "https://screamcasebot.onrender.com/api/open_case" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 7782281997,
    "case_id": 3,
    "initData": ""
  }'

# Ожидаемый ответ:
{
  "success": true,
  "item": {
    "price": 123,
    "name": "Diamond Rings",
    "image": "/asset/Gifts/1200S_Diamond_Rings.webp"
  },
  "deducted": 15
}
```

### 4. Проверка инвентаря (GET /api/inventory)

```bash
# Получить все открытые предметы пользователя
curl -X GET "https://screamcasebot.onrender.com/api/inventory?user_id=7782281997" \
  -H "Content-Type: application/json"

# Ожидаемый ответ:
{
  "user_id": 7782281997,
  "total_items": 5,
  "total_value": 2500,
  "items": [
    {
      "name": "Diamond Rings",
      "image": "/asset/Gifts/1200S_Diamond_Rings.webp",
      "price": 1200,
      "count": 2,
      "items": [...]
    }
  ]
}
```

### 5. Проверка списка кейсов (GET /api/cases)

```bash
curl -X GET "https://screamcasebot.onrender.com/api/cases" \
  -H "Content-Type: application/json"
```

## Что было исправлено

### 1. Auth Middleware (Fallback для dev режима)
- ✅ GET запросы с query параметром `user_id` теперь работают даже без валидного initData
- ✅ POST запросы по-прежнему требуют валидный initData
- ✅ Логирование показывает fallback режим

### 2. API Balance
- ✅ Убедитесь что возвращает колонку `stars` из таблицы `users`
- ✅ Добавлено логирование текущего баланса
- ✅ Fallback на дефолт значения если пользователя нет в БД

### 3. API Invoice  
- ✅ Теперь принимает user_id из auth или из body
- ✅ Добавлена проверка существования пользователя
- ✅ Улучшено логирование

## Проверка в Telegram Mini App

1. Откройте приложение через Telegram бота
2. Приложение должно показать баланс пользователя (100,000 звёзд для админа)
3. Нажмите "Пополнить баланс" - должен создаться инвойс без ошибок
4. Откройте кейс - должна запуститься анимация рулетки
5. Проверьте инвентарь - должны появиться открытые предметы

## Логирование

Сервер логирует:
- ✅ Попытки доступа с fallback user_id
- ✅ Получение баланса (с числом звёзд)
- ✅ Создание инвойсов (с комментарием)
- ✅ Открытие кейсов (с названием выигранного предмета)
- ✅ Ошибки авторизации
