# Mini IPAM & DCIM v8.2.0 (Modular + REST API + MCP + Optional Token Auth)
## Быстрый старт
1. `pip install -r requirements.txt`
2. `python migrate_to_v8.py`
3. `python app.py` -> http://127.0.0.1:5000

## Аутентификация REST API
- По умолчанию аутентификация отключена (если нет активных токенов в БД и не задана переменная `IPAM_API_TOKEN`).
- После создания первого токена в `/config` запросы к `/api/v1/*` требуют заголовок `Authorization: Bearer <token>` или `X-API-Key: <token>`.
