# MAX Bot API и мини-приложения — гайд по разработке

Сводный гайд по разработке чат-ботов и мини-приложений для мессенджера MAX. Собран по официальной документации [dev.max.ru](https://dev.max.ru/docs) (снимок от 2026-09-22), OpenAPI-схеме [max-messenger/api-schema](https://github.com/max-messenger/api-schema) (v0.0.33) и Python-библиотеке [`maxapi`](https://github.com/love-apples/maxapi) (1.2.x).

Каждый раздел ссылается на **локальную копию** первоисточника (`reference/…`) и на оригинал. Полные параметры методов смотрите в [`reference/api/methods/`](reference/api/methods/), все типы — в [`openapi/SCHEMA.md`](openapi/SCHEMA.md). Карта всех файлов — в [README.md](README.md).

> Документация MAX быстро меняется: за 2026 год сменился домен API, удалён `GET /chats`, запрещены HTTP-вебхуки. Если что-то не сходится, обновите снимок командой из раздела [Обновление](#15-обновление-локальной-документации) или сверьтесь с [changelog API](reference/api/changelog-api.md).

---

## 0. Главное: что легко упустить

| # | Факт | Источник |
|---|---|---|
| 1 | Базовый URL — **`https://platform-api2.max.ru`**. Старый `platform-api.max.ru` не использовать (с 19.07.2026) | [api/index](reference/api/index.md), [changelog](reference/api/changelog-api.md) |
| 2 | Токен передаётся **только в заголовке** `Authorization: <token>`, без `Bearer`. Query-параметр `access_token` больше не работает | [api/index](reference/api/index.md) |
| 3 | TLS-сертификат API выдан **Russian Trusted Root CA (Минцифры)**. Python (`httpx`, `requests`, `aiohttp`, `urllib`) из коробки падает с `CERTIFICATE_VERIFY_FAILED`. Добавьте [`certs/russiantrustedca.pem`](certs/russiantrustedca.pem) в доверенные (см. [§13](#13-python-maxapi-и-сырые-запросы)). `maxapi` делает это сам | проверено 2026-09-22 |
| 4 | **Production — только Webhook.** Long Polling подходит лишь для разработки: 2 RPS, батч до 100 событий, TTL событий 24 ч. Одновременно использовать оба способа нельзя: при активной webhook-подписке `GET /updates` не работает | [POST /subscriptions](reference/api/methods/POST_subscriptions.md), [maxapi](python-maxapi/docs/guides/webhook_vs_polling.md) |
| 5 | Webhook-endpoint: **HTTPS, порт 443, сертификат доверенного CA** (самоподписанные не принимаются), ответ **200 за ≤30 с**. Если 8 часов подряд нет успешного ответа, **подписка удаляется автоматически** | [POST /subscriptions](reference/api/methods/POST_subscriptions.md) |
| 6 | Лимиты: **30 RPS** на весь API, **2 сообщения/ответа/правки/удаления в секунду** в один чат | [prepare](reference/platform/chatbots/bots-coding/prepare.md), [POST /messages](reference/api/methods/POST_messages.md) |
| 7 | **`GET /chats` удалён** (июнь 2026). Список чатов бота нужно вести самим: сохранять `chat_id` из событий `bot_added` / `bot_started` / `message_created`, удалять по `bot_removed` | [GET /chats](reference/api/methods/GET_chats.md) |
| 8 | **`POST /chats/{id}/members` удаляется 30.09.2026.** Добавлять людей в чаты через API нельзя, создавать чаты ботом тоже нельзя | [POST members](reference/api/methods/POST_chats_chatId_members.md), Q&A хакатона |
| 9 | В **групповых чатах** бот получает `message_created`, только если он **администратор с правом `read_all_messages`**. Без этого права вебхук не приходит | [SCHEMA: MessageCreatedUpdate](openapi/SCHEMA.md#messagecreatedupdate), [admins](reference/api/methods/POST_chats_chatId_members_admins.md) |
| 10 | Добавление бота в групповые чаты **по умолчанию запрещено** настройкой «Приватность» на платформе партнёров (business.max.ru). Нашего бота создавали организаторы: если нужен сценарий с домовыми чатами, просите их включить эту настройку | [bots-create/manage](reference/platform/chatbots/bots-create/manage.md), [faq/chatbots](reference/faq/chatbots.md) |
| 11 | Файл сразу после загрузки может быть ещё не готов: `POST /messages` вернёт `attachment.not.ready`. Нужен retry с растущей паузой | [media](reference/api/use-cases/sending-messages/media.md) |
| 12 | **Массовые, рекламные и авторизационные (OTP) рассылки через API запрещены** правилами платформы (п. 1.5 требований) | [legal/requirements](reference/platform/legal/requirements.md) |
| 13 | `type=photo` устарел, используйте `type=image`. Права `edit_message`, `delete_message`, `post_edit_delete_message` заменены на `edit`, `delete`, `write` | [POST /uploads](reference/api/methods/POST_uploads.md), [admins](reference/api/methods/POST_chats_chatId_members_admins.md) |
| 14 | Мини-приложение существует **только внутри бота**: URL задаётся в настройках бота, только `https://`, до 1024 символов | [webapps/introduction](reference/platform/webapps/introduction.md) |
| 15 | Данные мини-приложения (`initData`) **обязательно проверяйте на сервере** по HMAC. `initDataUnsafe` для проверки не годится | [webapps/validation](reference/platform/webapps/validation.md) |

---

## 1. Наш бот (хакатон)

- Бот выдан организаторами: **`@t446_hakaton_max_bot`** (`user_id` 411198009, имя «Хакатон МАХ 446»). Ссылка: `https://max.ru/t446_hakaton_max_bot`.
- Токен лежит в `backend/.env` → `MAX_TOKEN`. Не коммитить и не выводить в логи.
- Состояние на 2026-09-22: webhook-подписок нет, команды (`/me/commands`) не заданы.
- Никнейм менять нельзя: по словам организаторов, переименование будет только у финалистов. Логотип, описание и настройки мини-приложения задаются на business.max.ru, доступ к ней у организаторов.
- Для мини-приложения ссылку нужно отправить через форму организаторов (см. [`case/README.md`](../../case/README.md)).
- Требования хакатона к боту (из Q&A-сессии): вебхуки, HTTPS, бот онлайн всё время проверки (30.09–14.10), код в этот период не менять. Подробнее — [`case/webinars/02-qna-session-summary.md`](../../case/webinars/02-qna-session-summary.md).

---

## 2. Основы API

Источник: [reference/api/index.md](reference/api/index.md) · [dev.max.ru/docs-api](https://dev.max.ru/docs-api)

```bash
curl "https://platform-api2.max.ru/me" -H "Authorization: $MAX_TOKEN"
```

- REST + JSON. `GET` читает, `POST` создаёт, `PUT` редактирует, `PATCH` частично изменяет, `DELETE` удаляет.
- Идентификаторы: `user_id` и `chat_id` — это int64 (у групповых чатов `chat_id` бывает отрицательным), `mid` сообщения — строка вида `mid.xxxx`.
- Время везде в **Unix-миллисекундах**. Исключение: `auth_date` в `initData` мини-приложения, он в секундах.
- Коды ответа: `200` OK, `400` неверный запрос, `401` неверный токен, `403` нет прав или бот остановлен пользователем, `404` не найдено, `405`, `429` превышен лимит, `500`, `503`.
- Тело ошибки ([SCHEMA: Error](openapi/SCHEMA.md#error)):
  ```json
  {"code": "verify.token", "message": "No access token"}
  ```
  Известные коды: `verify.token` (нет или неверный токен), `attachment.not.ready` (файл ещё обрабатывается), `File extension is forbidden` (неподдерживаемый тип загрузки).
- Многие изменяющие методы возвращают `200` даже при неудаче: `{"success": false, "message": "..."}`. **Проверяйте `success`.**
- OpenAPI-спецификация: [`openapi/schema.yaml`](openapi/schema.yaml). Из неё можно сгенерировать клиент (например, `openapi-python-client`). В ней описаны все типы, в том числе варианты `Update` и вложений, которых нет на страницах сайта.

### Все методы

| Метод | Назначение | Локальная копия |
|---|---|---|
| `GET /me` | Инфо о боте | [GET_me](reference/api/methods/GET_me.md) |
| `PATCH /me/commands` | Команды бота (подсказки при вводе `/`), до 32 | [PATCH_me_commands](reference/api/methods/PATCH_me_commands.md) |
| `POST /subscriptions` | Подписаться на webhook | [POST_subscriptions](reference/api/methods/POST_subscriptions.md) |
| `GET /subscriptions` | Список подписок | [GET_subscriptions](reference/api/methods/GET_subscriptions.md) |
| `DELETE /subscriptions?url=` | Отписаться | [DELETE_subscriptions](reference/api/methods/DELETE_subscriptions.md) |
| `GET /updates` | Long Polling (только dev) | [GET_updates](reference/api/methods/GET_updates.md) |
| `POST /messages` | Отправить сообщение (`user_id` или `chat_id`) | [POST_messages](reference/api/methods/POST_messages.md) |
| `GET /messages` | Сообщения чата (бот-админ) или по `message_ids` | [GET_messages](reference/api/methods/GET_messages.md) |
| `GET /messages/{mid}` | Одно сообщение | [GET_messages_messageId](reference/api/methods/GET_messages_messageId.md) |
| `PUT /messages?message_id=` | Редактировать своё сообщение | [PUT_messages](reference/api/methods/PUT_messages.md) |
| `DELETE /messages?message_id=` | Удалить сообщение | [DELETE_messages](reference/api/methods/DELETE_messages.md) |
| `POST /answers?callback_id=` | Ответ на нажатие callback-кнопки | [POST_answers](reference/api/methods/POST_answers.md) |
| `POST /uploads?type=` | Получить URL для загрузки файла | [POST_uploads](reference/api/methods/POST_uploads.md) |
| `GET /videos/{token}` | Инфо о видео, URL воспроизведения | [GET_videos_videoToken](reference/api/methods/GET_videos_videoToken.md) |
| `GET /chats/{id}` | Инфо о чате или канале | [GET_chats_chatId](reference/api/methods/GET_chats_chatId.md) |
| `PATCH /chats/{id}` | Изменить название, описание, иконку, закреп (бот-админ) | [PATCH_chats_chatId](reference/api/methods/PATCH_chats_chatId.md) |
| `POST /chats/{id}/actions` | «Печатает…», «отправляет фото…» | [POST_chats_chatId_actions](reference/api/methods/POST_chats_chatId_actions.md) |
| `GET/PUT/DELETE /chats/{id}/pin` | Закреп | [GET](reference/api/methods/GET_chats_chatId_pin.md) · [PUT](reference/api/methods/PUT_chats_chatId_pin.md) · [DELETE](reference/api/methods/DELETE_chats_chatId_pin.md) |
| `GET /chats/{id}/members` | Участники (бот-админ), пагинация `marker`, `count` ≤100 | [GET_chats_chatId_members](reference/api/methods/GET_chats_chatId_members.md) |
| `DELETE /chats/{id}/members?user_id=` | Исключить участника (`block=true` — заблокировать) | [DELETE_chats_chatId_members](reference/api/methods/DELETE_chats_chatId_members.md) |
| `POST /chats/{id}/members` | ⚠️ Добавить участников — **удаляется 30.09.2026** | [POST_chats_chatId_members](reference/api/methods/POST_chats_chatId_members.md) |
| `GET /chats/{id}/members/me` | Членство и права бота в чате | [GET_chats_chatId_members_me](reference/api/methods/GET_chats_chatId_members_me.md) |
| `DELETE /chats/{id}/members/me` | Бот выходит из чата | [DELETE_chats_chatId_members_me](reference/api/methods/DELETE_chats_chatId_members_me.md) |
| `GET /chats/{id}/members/admins` | Администраторы | [GET_…_admins](reference/api/methods/GET_chats_chatId_members_admins.md) |
| `POST /chats/{id}/members/admins` | Назначить админа или обновить права (семантика PUT) | [POST_…_admins](reference/api/methods/POST_chats_chatId_members_admins.md) |
| `DELETE /chats/{id}/members/admins/{uid}` | Снять админа | [DELETE_…_admins_userId](reference/api/methods/DELETE_chats_chatId_members_admins_userId.md) |
| `GET/POST/PUT/DELETE /messages/{mid}/comments` | Комментарии к постам канала | [use-case](reference/api/use-cases/comment-moderation.md), [методы](reference/api/methods/) |
| ~~`GET /chats`~~ | Удалён, см. [§6](#6-чаты-участники-права) | [GET_chats](reference/api/methods/GET_chats.md) |

---

## 3. Получение событий

Источники: [POST /subscriptions](reference/api/methods/POST_subscriptions.md), [GET /updates](reference/api/methods/GET_updates.md), [Update](reference/api/objects/Update.md), [SCHEMA: Update](openapi/SCHEMA.md#update), [faq/events](reference/faq/events.md)

### Webhook (единственный вариант для прода)

```bash
curl -X POST "https://platform-api2.max.ru/subscriptions" \
  -H "Authorization: $MAX_TOKEN" -H "Content-Type: application/json" \
  -d '{"url": "https://bot.example.ru/webhook",
       "update_types": ["message_created", "message_callback", "bot_started", "bot_added", "bot_removed"],
       "secret": "random_secret_5_to_256_chars"}'
```

Требования к endpoint:
- только `https://`, **порт 443** (порт в URL не указывается);
- сертификат доверенного CA или Минцифры, CN/SAN совпадает с доменом, **полная цепочка**. Let's Encrypt подходит;
- ответ **HTTP 200 в течение 30 с**. Отвечайте сразу, тяжёлую обработку уносите в фон или очередь;
- `secret` (`^[a-zA-Z0-9_-]{5,256}$`) приходит в заголовке **`X-Max-Bot-Api-Secret`**. Проверяйте его и отклоняйте запросы с неверным значением.

Повторы при неудаче: до 10 попыток через 60 с, 150 с, 375 с, … (×2,5). Если за **8 часов** нет ни одного успешного ответа, бот **автоматически отписывается**. После простоя проверьте `GET /subscriptions` и переподпишитесь (удобно делать это при каждом старте сервиса).

**Дубли возможны**: одно и то же событие может прийти повторно. Обработку делайте идемпотентной, например дедуплицируйте по `update_type + timestamp + mid/callback_id`.

`update_types` — фильтр. Если параметр не указан, приходят все типы. Для диплинков обязательно нужен `bot_started`.

### Long Polling (только локальная разработка)

`GET /updates?limit=100&timeout=30&marker=<из прошлого ответа>&types=message_created,message_callback`

- Ответ: `{"updates": [...], "marker": N}`. Передавайте `marker` в следующий запрос, тогда всё, что было до него, считается прочитанным. Без `marker` приходит только последнее обновление.
- Ограничения (из документации `maxapi`, действуют с 11.05.2026): 2 RPS, таймаут 30 с, батч ≤100, **события живут 24 ч**.
- Если активна webhook-подписка, polling не работает. Сначала выполните `DELETE /subscriptions?url=...` (в `maxapi` — `bot.delete_webhook()`).
- Удобный dev-вариант без публичного сервера: polling локально, webhook на сервере. Либо webhook через туннель с валидным сертификатом (cloudflared и т. п.).

### Типы событий (`update_type`)

Точные поля — в [SCHEMA.md](openapi/SCHEMA.md#update). Все события содержат `update_type` и `timestamp` (мс).

| `update_type` | Когда | Ключевые поля |
|---|---|---|
| `message_created` | Новое сообщение или пост. **В группах — только если бот админ с `read_all_messages`** | `message` ([Message](openapi/SCHEMA.md#message)), `user_locale` (только диалоги) |
| `message_callback` | Нажата callback-кнопка | `callback{callback_id, payload, user, timestamp}`, `message` (может быть `null`), `user_locale` |
| `message_edited` | Сообщение изменено | `message` |
| `message_removed` | Сообщение удалено | `message_id`, `chat_id`, `user_id` |
| `bot_started` | Пользователь нажал «Начать» или перешёл по диплинку `?start=` | `chat_id`, `user`, **`payload`** (диплинк), `user_locale` |
| `bot_stopped` | Пользователь остановил или удалил бота | `chat_id`, `user` |
| `dialog_removed` / `dialog_cleared` / `dialog_muted` / `dialog_unmuted` | Действия с диалогом | `chat_id`, `user` |
| `bot_added` | Бота добавили в чат или канал | `chat_id`, `user`, `is_channel` |
| `bot_removed` | Бота удалили из чата или канала | `chat_id`, `user`, `is_channel` |
| `user_added` | В чат добавлен или вошёл по ссылке пользователь | `chat_id`, `user`, `inviter_id`, `is_channel` |
| `user_removed` | Пользователь вышел или удалён | `chat_id`, `user`, `admin_id`, `is_channel` |
| `chat_title_changed` | Сменилось название | `chat_id`, `user`, `title` |
| `bot_admin_permissions_changed` | Изменились права бота-админа | см. схему |
| `comment_created` / `comment_edited` / `comment_removed` | Комментарии к постам канала (на свои действия бот событий не получает) | см. схему |

Где взять `chat_id` и `user_id` в `message_created`: `message.recipient.chat_id`, `message.recipient.chat_type` (`dialog` / `chat` / `channel`), `message.sender.user_id`. Текст — `message.body.text`, вложения — `message.body.attachments`, id сообщения — `message.body.mid`.

---

## 4. Отправка сообщений

Источники: [POST /messages](reference/api/methods/POST_messages.md), [форматирование](reference/api/use-cases/sending-messages/text-formatting.md), [SCHEMA: NewMessageBody](openapi/SCHEMA.md#newmessagebody)

```bash
curl -X POST "https://platform-api2.max.ru/messages?user_id=123" \
  -H "Authorization: $MAX_TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "**Заявка №42** принята", "format": "markdown"}'
```

- Адресат передаётся в **query**: `user_id` (личка) **или** `chat_id` (чат или канал).
- Тело ([NewMessageBody](openapi/SCHEMA.md#newmessagebody)):
  - `text` — до **4000** символов;
  - `attachments[]` — вложения;
  - `format`: `markdown` | `html`;
  - `notify` (по умолчанию `true`; `false` — без push, для каналов нельзя);
  - `link: {type: "reply" | "forward", mid}` — ответ или пересылка.
- Query `disable_link_preview=true` отключает превью ссылок.
- Ответ: `{"message": Message}`. Сохраните `message.body.mid`, чтобы потом редактировать сообщение.
- **Лимит 2 сообщения/с в один чат** (ставьте в очередь) и **30 RPS** на весь API.
- Редактирование `PUT /messages?message_id=`:
  - в диалоге сообщения с `inline_keyboard` можно править без срока, остальные — только в течение **7 суток**;
  - в группах и каналах ограничения по сроку нет;
  - передача `attachments: []` удаляет все вложения, `null` или отсутствие поля оставляет их без изменений.
- Удаление `DELETE /messages?message_id=`: в диалоге — только свои сообщения; в группе или канале — любые, если бот админ с правом удаления.
- «Печатает…»: `POST /chats/{chatId}/actions {"action": "typing_on"}` (есть также `sending_photo` / `video` / `audio` / `file`).

### Форматирование

| Эффект | Markdown | HTML |
|---|---|---|
| курсив | `*t*` / `_t_` | `<i>`, `<em>` |
| жирный | `**t**` / `__t__` | `<b>`, `<strong>` |
| зачёркнутый | `~~t~~` | `<s>`, `<del>` |
| подчёркнутый | `++t++` | `<u>`, `<ins>` |
| моноширинный | `` `t` `` | `<code>`, `<pre>` |
| ссылка | `[t](https://…)` | `<a href="…">` |
| упоминание | `[Имя Фамилия](max://user/<user_id>)` | `<a href="max://user/<user_id>">Имя Фамилия</a>` |
| выделение | `^^t^^` | `<mark>` |
| заголовок | `# t` | `<h1>`…`<h6>` (выглядят одинаково) |
| цитата | `> t` | `<blockquote>` |

В упоминании указывайте полное имя из профиля. В комментариях к постам ссылки и упоминания не работают.

---

## 5. Клавиатуры и callback-кнопки

Источники: [keyboard](reference/api/use-cases/sending-messages/keyboard.md), [POST /answers](reference/api/methods/POST_answers.md), [SCHEMA: Button](openapi/SCHEMA.md#button)

```json
{
  "text": "Что случилось?",
  "attachments": [{
    "type": "inline_keyboard",
    "payload": {"buttons": [
      [{"type": "callback", "text": "💧 Протечка", "payload": "issue:leak"},
       {"type": "callback", "text": "💡 Свет", "payload": "issue:light"}],
      [{"type": "link", "text": "Сайт УК", "url": "https://example.ru"}],
      [{"type": "open_app", "text": "Открыть приложение", "web_app": "t446_hakaton_max_bot"}]
    ]}
  }]
}
```

- Лимиты: до **210 кнопок**, **30 рядов**, **7 кнопок в ряду**. В ряду с кнопками `link` / `open_app` / `request_geo_location` / `request_contact` — не больше **3**. Текст кнопки — 1–128 символов, на экране обрезается; кнопки в ряду одной ширины.
- Типы ([SCHEMA](openapi/SCHEMA.md#button)):

| `type` | Поля | Что делает |
|---|---|---|
| `callback` | `payload` (≤1024) | Шлёт боту `message_callback` |
| `link` | `url` (≤2048) | Открывает ссылку |
| `message` | — | Отправляет от пользователя текст кнопки |
| `request_contact` | — | Пользователь делится контактом и номером (приходит вложение `contact` с `hash`) |
| `request_geo_location` | `quick?` (`true` — без подтверждения) | Пользователь отправляет геолокацию (вложение `location`) |
| `open_app` | `web_app` (ник бота с мини-приложением), `payload?` (≤512, `[\w-]*`), `contact_id?` | Открывает мини-приложение |
| `clipboard` | `payload` | Копирует `payload` в буфер обмена |

- При пересылке сообщения в другой чат кнопки теряются.

### Обработка нажатия

1. Приходит `message_callback`: `callback.callback_id`, `callback.payload`, `callback.user`, `message` (исходное сообщение).
2. Ответьте **`POST /answers?callback_id=<id>`** ([CallbackAnswer](openapi/SCHEMA.md#callbackanswer)):
   - `{"notification": "Готово!"}` — всплывающее уведомление;
   - и/или `{"message": NewMessageBody}` — **заменить** исходное сообщение, например обновить текст и клавиатуру (удобно для пошаговых форм без спама сообщениями).
3. Лимит: 2 ответа/с в один чат.

### Проверка номера из `request_contact`

Вложение `contact`: `payload.vcf_info` (vCard), `payload.max_info` (User), `payload.hash`. Номер принадлежит пользователю, если `hash == HMAC-SHA256(key=bot_token, msg=vcf_info)`, hex. Перед хешированием превратите `\r\n` в `vcf_info` в настоящие переводы строк. Если контакт отправлен вручную через 📎, поля `hash` нет и проверка невозможна. Данные из `request_contact` можно использовать **только в этом боте**.

```python
import hashlib, hmac

def contact_is_verified(vcf_info: str, hash_: str, bot_token: str) -> bool:
    vcf = vcf_info.replace("\\r\\n", "\r\n")  # если пришли экранированные символы
    calc = hmac.new(bot_token.encode(), vcf.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, hash_)
```

> В документации записано `HMAC-SHA256(access_token, vcf_info)`, и порядок «ключ/сообщение» явно не указан. Выше первым аргументом взят ключ, по аналогии с валидацией мини-приложений. Проверьте на реальном контакте.

---

## 6. Чаты, участники, права

Источники: [GET /chats (удалён)](reference/api/methods/GET_chats.md), [getting-chat-id](reference/api/use-cases/getting-chat-id.md), [admins](reference/api/methods/POST_chats_chatId_members_admins.md), [ChatMember](reference/api/objects/ChatMember.md)

**Как получить `chat_id`:** только из событий (`bot_added`, `bot_started`, `message_created`, `user_added` …) или в мини-приложении из `WebApp.initData.chat.id`. **Храните реестр чатов у себя** (БД):
- добавляйте `chat_id` при `bot_added` и при первом событии из чата;
- удаляйте или помечайте при `bot_removed`;
- учитывайте дубли событий.

> Эксперт трека «Умный город» на Q&A-сессии: «бот помнит только последнюю 1000 чатов». Судя по всему, это ограничение старого `GET /chats`, из-за которого его и убрали. При своём реестре в БД это ограничение не мешает. Для тысяч домовых чатов нужен собственный учёт.

Тип чата (`Chat.type`): `dialog` | `chat` | `channel`. Статус (`Chat.status`): `active` | `removed` | `left` | `closed`.

**Права администратора** (`permissions`):

| Право | Смысл | Кому |
|---|---|---|
| `read_all_messages` | Читать все сообщения. **Без него бот-админ не получает вебхуки о сообщениях в группе** и не может закреплять, редактировать или удалять | пользователи и боты |
| `write` | Править и удалять сообщения в группах, писать посты и комментарии в каналах | требует `read_all_messages` |
| `edit` / `delete` | Править / удалять посты и комментарии в каналах | требует `read_all_messages` |
| `pin_message` | Закреплять | требует `read_all_messages` |
| `change_chat_info` | Менять название, описание, иконку | все |
| `add_remove_members` | Добавлять и удалять участников (боты — только в чатах) | все |
| `add_admins` | Назначать и снимать админов | все |
| `edit_link` | Менять ссылку чата | чаты |
| `can_call` | Звонки в группе (ставится автоматически) | чаты |
| `view_stats` | Статистика канала | только владелец |

Устаревшие названия прав, которые ещё могут прийти в ответах: `edit_message` → `edit`, `delete_message` → `delete`, `post_edit_delete_message` → `write`.

Чего **нет** в API: создать чат, добавить участника (с 30.09.2026), получить список чатов бота, узнать, включены ли у пользователя уведомления.

---

## 7. Медиа и вложения

Источники: [media](reference/api/use-cases/sending-messages/media.md), [POST /uploads](reference/api/methods/POST_uploads.md), [attachment-types](reference/api/use-cases/sending-messages/attachment-types.md), [стикеры и контакты](reference/api/use-cases/sending-messages/another-attachments.md)

Процесс загрузки:
1. `POST /uploads?type=image|video|audio|file` → `{"url": ..., "token"?: ...}`. Для `video` и `audio` токен приходит **сразу в этом ответе**.
2. `POST <url>` с multipart (`-F "data=@file"`). Для `image` ответ — `{"photos": {"<id>": {"token": "..."}}}`, для `file` — `{"fileId": ..., "token": "..."}`, для `audio` и `video` — `<retval>1</retval>`.
3. `POST /messages` с `{"type": "<тип>", "payload": {"token": "<token>"}}`.
4. Если ответ `attachment.not.ready`, повторите с растущей паузой. Часто отправляемые файлы загрузите заранее и переиспользуйте токен.

Одна ссылка для загрузки — один файл. Токен можно переиспользовать. Картинку можно отправить без загрузки: `{"type": "image", "payload": {"url": "https://..."}}`, но это менее надёжно.

| Тип | Форматы | Лимит |
|---|---|---|
| `image` | JPG, JPEG, PNG, GIF, TIFF, BMP, HEIC | 50 МБ **и** ≤7680×7680 |
| `video` | MP4, MOV, MKV, WEBM | 250 МБ |
| `audio` | MP3, WAV, M4A … | 256 МБ **и** ≤60 мин |
| `file` | TXT, DOC, PDF … | 4 ГБ |
| `sticker` | `code` или `url` | 1 на сообщение |
| `contact` | `contact_id` или `vcf_info` (+ `name`) | 1 (+ 1 клавиатура) |
| `location` | `latitude`, `longitude` | — |
| `share` | `url` (превью ссылки) | — |
| `inline_keyboard` | см. [§5](#5-клавиатуры-и-callback-кнопки) | 1 на сообщение |

Комбинации: до **12** вложений image+video и одна клавиатура. `file` отправляется только с клавиатурой, без медиа, и в сообщении может быть **только один** файл.

Входящие вложения от пользователя приходят в `message.body.attachments[]`. У `image` / `video` / `audio` / `file` есть `payload.url` и `payload.token`. Для видео подробности даёт `GET /videos/{token}`.

---

## 8. Команды бота

[PATCH /me/commands](reference/api/methods/PATCH_me_commands.md): `{"commands": [{"name": "start", "description": "Начать"}, ...]}`, до 32 команд. Пустой массив удаляет все. Встроенных команд у платформы нет: `/start` — обычный текст в `message_created`, а первое открытие бота приходит отдельным событием `bot_started`.

---

## 9. Диплинки

Источники: [prepare#диплинки](reference/platform/chatbots/bots-coding/prepare.md), [webapps/introduction#диплинки](reference/platform/webapps/introduction.md), [faq/deeplinks](reference/faq/deeplinks.md)

| Ссылка | Что делает | Ограничения | Где читать payload |
|---|---|---|---|
| `https://max.ru/<bot>?start=<payload>` | Открывает бота | payload ≤**128** символов, иначе теряется. По схеме `BotStartedUpdate.payload` ≤512 — ориентируйтесь на 128 | `bot_started.payload` |
| `https://max.ru/<bot>?startapp=<payload>` | Открывает мини-приложение | ≤**512**, только `A-Z a-z 0-9 _ -` | `WebApp.initDataUnsafe.start_param` (и в `initData`) |
| `https://max.ru/:share?text=<urlencoded>` | Экран «Отправить в MAX» | iOS, Android, web; на десктопе пока нет | — |

Несколько параметров кодируйте в одну строку: `?start=house_123_flat_45`. **Не передавайте** в payload персональные данные в открытом виде, используйте короткие одноразовые токены. Пример использования: QR-код в подъезде → `https://max.ru/t446_hakaton_max_bot?start=house_<id>`.

---

## 10. Мини-приложения (Web Apps)

Источники: [introduction](reference/platform/webapps/introduction.md), [MAX Bridge](reference/platform/webapps/bridge.md), [validation](reference/platform/webapps/validation.md), [faq/miniapps](reference/faq/miniapps.md), UI-кит [MAX UI](https://dev.max.ru/ui) ([github](https://github.com/max-messenger/max-ui), Figma-гайдлайн там же)

- Обычный веб (HTML, JS, CSS, любой фреймворк) на **HTTPS**. URL задаётся в настройках бота: до 1024 символов, латиница, цифры, `.` и `-`. Если URL постоянный, после деплоя пользователи сразу получают новую версию.
- Хостинг: подойдёт любой с валидным HTTPS. В документации упомянуты [VK Cloud для мини-приложений](https://cloud.vk.com/promopage/max-mini-app/), GitHub Pages, Yandex Cloud.
- Запуск: кнопка в чате с ботом (вид кнопки — «Открыть», «Старт», «Играть» или без названия), кнопка `open_app`, диплинк `?startapp`.
- Одновременно открыто только одно мини-приложение.

### MAX Bridge

```html
<script src="https://st.max.ru/js/max-web-app.js"></script>
<script>
  const wa = window.WebApp;  // инициализация не нужна
  const initData = wa.initData;               // строка — отправляйте на бэкенд для проверки
  const u = wa.initDataUnsafe.user;           // {id, first_name, last_name, username, language_code, photo_url}
  const chat = wa.initDataUnsafe.chat;        // {id, type: 'DIALOG'|'CHAT'|'CHANNEL'}
  const startParam = wa.initDataUnsafe.start_param;
</script>
```

| API | Что делает | Ограничения |
|---|---|---|
| `initData`, `initDataUnsafe` | Стартовые данные: `query_id`, `auth_date`, `hash`, `user`, `chat`, `start_param`, `ip?` | Unsafe не использовать для доверия |
| `platform`, `version`, `deviceName` | `ios` / `android` / `desktop` / `web`, версия MAX, устройство | — |
| `getLaunchContext()` | `entryPoint`: `tabbar` \| `default` | Android ≥26.19.2, iOS ≥26.20.0 |
| `requestContact()` | Номер телефона → `{phone, authDate, hash}` | Проверять hash на сервере |
| `openLink(url)` / `openMaxLink(url)` | Внешний браузер / ссылка `max.ru` внутри MAX | Нужен клик пользователя |
| `downloadFile(url, name)` | Скачать файл по https | Нужен клик; `href download` не работает |
| `shareContent({text, link})` | Нативный шеринг | Не в web |
| `shareMaxContent({text, link} \| {mid, chatType})` | Шеринг внутри MAX; `mid` — сообщение, отправленное ботом | Нужен клик |
| `openCodeReader(fileSelect=true)` | Сканер QR (камера или файл) → `{value}` | — |
| `BackButton.show/hide/onClick/offClick` | Кнопка «Назад» в шапке | — |
| `enableClosingConfirmation()` | Предупреждение перед закрытием | — |
| `DeviceStorage.*` | Хранилище key-value на устройстве | Не в web |
| `SecureStorage.*` | Зашифрованное хранилище, ≤10 ключей | Не в web |
| `BiometricManager.*` | Биометрия | Не в web и desktop |
| `HapticFeedback.*` | Вибрация | Не в web и desktop |
| `NfcManager.*` | NFC | Только Android |
| `requestScreenMaxBrightness()`, `ScreenCapture.*`, `getViewportSize()` | Экран | — |

Ошибки приходят как reject: `{error: {code: "client.<method>.<reason>"}}`.

### Проверка `initData` на бэкенде (обязательно)

Алгоритм ([validation](reference/platform/webapps/validation.md)):
1. Разбейте строку `initData` по `&` на пары `key=value` и декодируйте значения из URL-кодировки.
2. Убедитесь, что `hash` встречается ровно один раз, сохраните его и уберите из списка.
3. Отсортируйте пары по ключу и соберите строку `k=v` через `\n`.
4. `secret = HMAC_SHA256(key="WebAppData", msg=bot_token)`.
5. `hex(HMAC_SHA256(key=secret, msg=launch_params)) == hash`.

Дополнительно проверяйте свежесть `auth_date`: он в секундах, рекомендуемое окно — 1 час.

```python
import hashlib, hmac, json, time
from urllib.parse import parse_qsl

def validate_init_data(init_data: str, bot_token: str, max_age_s: int = 3600) -> dict | None:
    """Возвращает распарсенные данные, если подпись верна, иначе None."""
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    keys = [k for k, _ in pairs]
    if keys.count("hash") != 1 or len(keys) != len(set(keys)):
        return None
    data = dict(pairs)
    received = data.pop("hash")
    launch_params = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, launch_params.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received):
        return None
    if time.time() - int(data.get("auth_date", 0)) > max_age_s:
        return None
    for k in ("user", "chat"):
        if k in data:
            data[k] = json.loads(data[k])
    return data
```

Типовая схема авторизации: фронт отправляет `WebApp.initData` в заголовке, например `Authorization: tma <initData>`. Бэкенд проверяет подпись и заводит сессию по `user.id`.

`requestContact()`: сравнить `hash` с HMAC-SHA256 от строки `authDate=…\nphone=…\nuserId=…` (ключи по алфавиту, `phone` без `+`) с токеном бота. Какой из аргументов ключ, в документации сказано неоднозначно. Проверьте оба варианта на реальных данных. Источник: [bridge](reference/platform/webapps/bridge.md).

---

## 11. Каналы, комментарии, Цифровой ID

- **Каналы**: бот-админ публикует посты через `POST /messages?chat_id=`. `notify=false` для каналов не работает. Комментарии доступны через `/messages/{postId}/comments` и события `comment_*`; сначала включите комментарии в канале. См. [comment-moderation](reference/api/use-cases/comment-moderation.md), [channels/manage](reference/platform/channels/manage.md), [faq/channels](reference/faq/channels.md).
- **Цифровой ID** — QR-код или NFC в MAX для подтверждения возраста и льготных статусов (студент, многодетный, пенсионер, инвалидность) на кассе. Подключают юрлица и ИП отдельным токеном и отдельным API. Бот этого не умеет, а мини-приложению в хакатоне это недоступно. См. [digital-id](reference/platform/digital-id.md), [faq/digital-id](reference/faq/digital-id.md).

---

## 12. Правила платформы, которые влияют на код

Источники: [requirements](reference/platform/legal/requirements.md), [rules](reference/platform/legal/rules.md), [privacy](reference/platform/legal/privacy.md), [пользовательское соглашение](https://legal.max.ru/ps)

- **Нельзя**:
  - рассылать через API авторизационные, транзакционные и сервисные сообщения, а также массовые, рекламные и маркетинговые рассылки (кроме случаев, прямо разрешённых договором с MAX). Отправлять коды авторизации через диплинки тоже запрещено;
  - вводить пользователей в заблуждение, публиковать запрещённый контент.
- **Обязательно**:
  - показывать пользователю сведения об операторе, **политику обработки ПДн** и условия использования;
  - если есть пользовательский контент, пользователь явно принимает условия, а незаконный контент удаляется по жалобе;
  - защищаться от подмены и накрутки запросов (проверка подписи `initData`, secret вебхука);
  - корректно обрабатывать ошибки и нестандартный ввод;
  - корректно обрабатывать отказ в разрешениях.
- ПДн: разработчик — самостоятельный оператор, нужны правовые основания (152-ФЗ). Для хакатона — обезличенные или синтетические данные.

---

## 13. Python: `maxapi` и сырые запросы

Официальные SDK есть только для [TypeScript](https://github.com/max-messenger/max-bot-api-client-ts) ([docs](reference/platform/chatbots/bots-coding/js.md)) и [Go](https://github.com/max-messenger/max-bot-api-client-go) ([docs](reference/platform/chatbots/bots-coding/go.md), фреймворк [maxbot](https://github.com/max-messenger/maxbot)). Для Python есть **`maxapi`** от сообщества, в стиле aiogram (`Bot`, `Dispatcher`, `Router`, `F`, фильтры, middleware, FSM). У MAX есть «проверенный форк» [max-messenger/max-botapi-python](https://github.com/max-messenger/max-botapi-python), но он **застыл на июле 2025**, поэтому берите upstream: `pip install maxapi` (1.2.2, август 2026, Python ≥3.10). Upstream уже работает с `platform-api2` и сам поставляет CA Минцифры.

Локально: [README](python-maxapi/README.md) · [документация](python-maxapi/docs/index.md) · [гайды](python-maxapi/docs/guides/) (handlers, filters, keyboards, routers, middleware, context/FSM, webhook vs polling) · [15 примеров](python-maxapi/examples/). Context7: `/love-apples/maxapi`.

### Webhook-бот на FastAPI (по `examples/09_webhook_bot.py`)

```python
# pip install "maxapi[fastapi]" uvicorn
import os
from fastapi import FastAPI
from maxapi import Bot, Dispatcher, F
from maxapi.enums.update import UpdateType
from maxapi.filters.command import Command, CommandStart
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.webhook.fastapi import FastAPIMaxWebhook

bot = Bot(os.environ["MAX_TOKEN"])  # без аргумента берёт MAX_BOT_TOKEN
dp = Dispatcher()

@dp.on_started()
async def on_started() -> None:
    await bot.subscribe_webhook(
        url=os.environ["WEBHOOK_URL"],
        update_types=[UpdateType.MESSAGE_CREATED, UpdateType.MESSAGE_CALLBACK, UpdateType.BOT_STARTED],
        secret=os.environ["WEBHOOK_SECRET"],
    )

@dp.bot_started()
async def on_bot_started(event: BotStarted) -> None:
    # event.payload — значение из https://max.ru/<bot>?start=<payload>
    await bot.send_message(user_id=event.user.user_id, text=f"Привет! payload={event.payload}")

@dp.message_created(CommandStart())
async def on_start(event: MessageCreated) -> None:
    kb = InlineKeyboardBuilder()
    kb.row(CallbackButton(text="Протечка", payload="issue:leak"),
           CallbackButton(text="Свет", payload="issue:light"))
    await event.message.answer("Что случилось?", attachments=[kb.as_markup()])

@dp.message_callback(F.callback.payload.startswith("issue:"))
async def on_issue(event: MessageCallback) -> None:
    await event.answer(notification="Заявка принята", new_text=f"Тип: {event.callback.payload}")

webhook = FastAPIMaxWebhook(dp=dp, bot=bot, secret=os.environ["WEBHOOK_SECRET"])
app = FastAPI(lifespan=webhook.lifespan)
webhook.setup(app, path="/webhook")
# uvicorn module:app  (за nginx/Caddy с HTTPS на 443)
```

Для локальной отладки без HTTPS: `await bot.delete_webhook(); await dp.start_polling(bot)`.

> `F` — это [magic_filter](https://github.com/aiogram/magic-filter), как в aiogram, поэтому `.startswith()`, `==`, `&` и `|` работают. `MessageCallback.answer(notification=, new_text=, attachments=, …)` вызывает `POST /answers`. Подробнее — [filters](python-maxapi/docs/guides/filters.md), [handlers](python-maxapi/docs/guides/handlers.md).

### Сырые запросы (httpx) с CA Минцифры

```python
import ssl, certifi, httpx

ctx = ssl.create_default_context(cafile=certifi.where())
ctx.load_verify_locations("docs/max/certs/russiantrustedca.pem")  # Russian Trusted Sub CA (до 2027-03-06)

max_api = httpx.AsyncClient(
    base_url="https://platform-api2.max.ru",
    headers={"Authorization": MAX_TOKEN},
    verify=ctx,
    timeout=35,
)
r = await max_api.post("/messages", params={"user_id": uid}, json={"text": "Привет"})
```

В Docker-образе вместо этого можно положить сертификат в `/usr/local/share/ca-certificates/` и выполнить `update-ca-certificates`, а для Python выставить `SSL_CERT_FILE` или `REQUESTS_CA_BUNDLE` на общий бандл. Сертификат взят из пакета `maxapi` (`maxapi/client/russiantrustedca.pem`); его также можно скачать на Госуслугах (gu-st.ru, «Russian Trusted Root CA»).

---

## 14. Архитектура для хакатона: чек-лист

- [ ] Бэкенд принимает webhook на `https://<домен>/webhook` (443, валидный сертификат, например Let's Encrypt через Caddy или nginx), отвечает 200 сразу, обрабатывает в фоне.
- [ ] При старте: `GET /subscriptions` → если подписки нет, `POST /subscriptions` с `secret`. Проверка `X-Max-Bot-Api-Secret`.
- [ ] Идемпотентная обработка событий, очередь исходящих сообщений (≤2/с на чат, ≤30 RPS всего), retry при `429` / `5xx` / `attachment.not.ready`.
- [ ] Реестр `chat_id` в БД: `bot_added` / `bot_removed` / `message_created`.
- [ ] Для групповых чатов: бот — админ с `read_all_messages`, в настройках бота включено добавление в группы (согласовать с организаторами).
- [ ] Мини-приложение: HTTPS, MAX Bridge, проверка `initData` на бэкенде, ссылка отправлена организаторам через форму.
- [ ] Токен и secret только в переменных окружения, без логирования.
- [ ] Healthcheck плюс мониторинг: если сервис лежит больше 8 ч, подписка снимается.
- [ ] Политика ПДн и условия использования доступны пользователю (например, команда `/privacy` или ссылка в описании).
- [ ] Никаких массовых рассылок. Уведомления только в ответ на действия пользователя или по его подписке.

---

## 15. Обновление локальной документации

```bash
# из корня репозитория
uv run --with markdownify --with beautifulsoup4 --with pyyaml python docs/max/scripts/update_docs.py
```

Скрипт заново обходит `dev.max.ru/docs`, `/docs-api`, `/help` и перезаписывает `reference/`. Содержимое вкладок (примеры на Python, Go и Java и т. п.) достаётся из RSC-данных Next.js и дописывается в конец страницы разделом «Содержимое вкладок». Затем скрипт обновляет `openapi/schema.yaml`, `python-maxapi/` и генерирует `openapi/SCHEMA.md`. Этот гайд (`GUIDE.md`) написан вручную: после обновления просмотрите `reference/api/changelog-api.md` и `reference/platform/changelog-platform.md` и при необходимости поправьте разделы 0–14.

Известные огрехи конвертации: в части примеров кода на сайте потеряны отступы (это видно и на самом сайте). Страницы объектов (`reference/api/objects/`) показывают только первый вариант `Update` и вложений, полные описания смотрите в [`openapi/SCHEMA.md`](openapi/SCHEMA.md).

---

## Ссылки

- Документация платформы: https://dev.max.ru/docs · API: https://dev.max.ru/docs-api · FAQ: https://dev.max.ru/help · UI-кит: https://dev.max.ru/ui
- Платформа партнёров (управление ботом): https://business.max.ru/self · бот «MAX для бизнеса»: https://max.ru/business_bot
- GitHub: [api-schema](https://github.com/max-messenger/api-schema) · [TS SDK](https://github.com/max-messenger/max-bot-api-client-ts) · [Go SDK](https://github.com/max-messenger/max-bot-api-client-go) · [maxbot (Go)](https://github.com/max-messenger/maxbot) · [demo-bot-go](https://github.com/max-messenger/demo-bot-go) · [max-ui](https://github.com/max-messenger/max-ui) · [todolist-пример](https://github.com/max-messenger/max-bot-example-todolist) · [maxapi (Python)](https://github.com/love-apples/maxapi)
- Changelog: [API](reference/api/changelog-api.md) · [платформа](reference/platform/changelog-platform.md)
