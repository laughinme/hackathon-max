# Мини-приложение «Домовой»

Vite + React 19 + TypeScript, [MAX UI](https://dev.max.ru/ui), TanStack Query. В проде отдаётся бэкендом по `/` того же домена, что и `/api` ([D-011](../docs/DECISIONS.md)).

## Что умеет

- **Житель:** карточка дома и УО, кнопка «Сообщить о проблеме» (переход в чат с ботом: заявку оформляет бот), открытые и закрытые заявки, экран заявки с нормативным сроком, основанием, ответственным и историей; подтверждение выполнения или возврат в работу; после истечения срока — «Подготовить жалобу в жилинспекцию» (PDF приходит в чат с ботом); в демо-режиме — «⏩ Демо: срок истёк», чтобы пройти этот путь за минуту.
- **Диспетчер УО:** очередь по сроку со счётчиками «открыто / просрочено / аварийных / домов» и фильтрами, смена статуса с комментарием для жителя (житель получает уведомление в боте).
- Диплинк `https://max.ru/<бот>?startapp=t_<id заявки>` открывает заявку сразу.

## Структура

```
src/
  app/        провайдеры, стек экранов (navigation), стартовый экран по диплинку
  pages/      home (выбор по роли), resident, dispatcher, ticket
  features/   change-status (диспетчер), confirm-resolution, escalate, demo-expire (житель)
  entities/   ticket (хуки API, подписи, ячейка, срок, история), user
  shared/     api (fetch-клиент, типы из OpenAPI), lib (MAX Bridge, форматирование), ui
```

## Команды

```bash
npm ci
npm run dev          # http://localhost:5173, /api проксируется на localhost:8080
npm run lint && npm run typecheck && npm test
npm run build        # dist/ — его и отдаёт бэкенд (MINIAPP_DIR)
API_SCHEMA_URL=https://domovoy.prooood.ru/api/openapi.json npm run api:types
```

Вне MAX подписанного `initData` нет. Для разработки в браузере: на бэкенде `DEV_AUTH_ENABLED=true`, во `frontend/.env` — `VITE_DEV_USER_ID=<ваш MAX user_id>` (запросы уйдут с `Authorization: dev <id>`). В проде `DEV_AUTH_ENABLED` выключен.
