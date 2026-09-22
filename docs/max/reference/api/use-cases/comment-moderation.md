<!-- source: https://dev.max.ru/docs-api/use-cases/comment-moderation -->

# Модерация комментариев к постам в каналах

Чтобы отслеживать новые комментарии в канале через API и отвечать на них, предварительно [включите опцию комментариев](https://dev.max.ru/docs/channels/manage#%D0%9A%D0%B0%D0%BA%20%D0%B2%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BA%D0%BE%D0%BC%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%80%D0%B8%D0%B8%20%D0%B2%20%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB%D0%B5). Пока эта опция отключена, бот сможет читать, редактировать и удалять только старые комментарии

С помощью API MAX вы можете:

- [`POST /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/POST/messages/-messageId-/comments) — публиковать комментарии к посту
- [`PUT /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/PUT/messages/-messageId-/comments) — редактировать свои комментарии и те, что опубликованы от имени канала, — при наличии права администратора `edit`. [Подробнее о правах](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members/admins#%D0%94%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%BD%D1%8B%D0%B5%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B0%20%D0%B0%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B0)
- [`GET /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments) — получать все комментарии
- [`GET /messages/{messageId}/comments/{commentId}`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments/-commentId-) — получить комментарий с указанным ID
- [`DELETE /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/DELETE/messages/-messageId-/comments) — удалять комментарии. Рекомендуем заранее ознакомить подписчиков со списком стоп-слов для вашего канала

Ниже приведён один из возможных сценариев использования API MAX для комментариев в канале — вы можете придумать и реализовать свой

## Как модерировать комментарии с помощью бота и API MAX

1. **[Добавьте бота](https://dev.max.ru/docs/channels/manage#%D0%9A%D0%B0%D0%BA%20%D0%BF%D1%80%D0%B8%D0%B3%D0%BB%D0%B0%D1%81%D0%B8%D1%82%D1%8C%20%D0%BF%D0%BE%D0%BB%D1%8C%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D0%B5%D0%B9%20%D0%B2%20%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB) в канал как участника**
2. **Назначьте бота администратором канала** с правами на чтение, редактирование, публикацию и удаление постов. Это можно сделать:

   - [В интерфейсе мессенджера МАХ](https://dev.max.ru/docs/channels/manage#%D0%9A%D0%B0%D0%BA%20%D0%BD%D0%B0%D0%B7%D0%BD%D0%B0%D1%87%D0%B8%D1%82%D1%8C%20%D0%B0%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B0%20%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB%D0%B0)
   - Через API c помощью [`POST /chats/{chatId}/members/admins`](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members/admins). В объекте `permissions` нужно передать соответствующие значения `read_all_message`, `edit`, `write`, `delete`. Также понадобится [ID канала](https://dev.max.ru/docs-api/use-cases/getting-chat-id)

   Готово! Теперь боту доступно чтение, редактирование и удаление всех комментариев в канале: старых и новых, своих и других участников (пользователей и ботов —  исключая редактирование комментариев. Бот может редактировать свои комментарии и те, что опубликованы от имени канала)

 **Пример запроса**
```bash
curl -X POST "https://platform-api2.max.ru/chats/{chatId}/members/admins" \
-H "Authorization: {access_token}" \
-H "Content-Type: application/json" \
-d '{
"admins": [
  {
    "user_id": "{bot_id}",
    "permissions": [
      "read_all_messages",
      "edit",
      "write",
      "delete"
    ],
    "alias": "администраторам"
  }
]
}'
```
Если потребуется, позже вы сможете изменить права бота или удалить его из канала одним из способов, представленных в этом раскрывающемся списке

- [В интерфейсе МАХ](https://dev.max.ru/docs/channels/manage#%D0%9A%D0%B0%D0%BA%20%D1%83%D0%B1%D1%80%D0%B0%D1%82%D1%8C%20%D0%BF%D0%BE%D0%BB%D1%8C%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8F%20%D0%B8%D0%B7%20%D0%B0%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%BE%D0%B2%20%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB%D0%B0%20%D0%B8%D0%BB%D0%B8%20%D0%B8%D0%B7%D0%BC%D0%B5%D0%BD%D0%B8%D1%82%D1%8C%20%D0%B5%D0%B3%D0%BE%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B0) — доступно только администратору, который добавил бота в канал, и владельцу чата
- Через API MAX с помощью [`POST /chats/{chatId}/members/admins`](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members/admins) для изменения прав и [`DELETE /chats/{chatId}/members/me`](https://dev.max.ru/docs-api/methods/DELETE/chats/-chatId-/members/me) — для удаления бота. Для это понадобится токен авторизации этого бота `access_token`и [ID канала](https://dev.max.ru/docs-api/use-cases/getting-chat-id)

3. **Подпишитесь на обновления о событиях с ботом через Webhook** с помощью [`POST /subscriptions`](https://dev.max.ru/docs-api/methods/POST/subscriptions). В запросе в объекте `update_types` укажите список событий, которые вы хотите получать. Для работы с комментариями это:

   - `comment_created` — новый комментарий
   - `comment_removed` — комментарий удалён
   - `comment_edited` — комментарий изменён

   После подписки события будут приходить на указанный в запросе Webhook-endpoint. События приходят в виде HTTPS `POST`-запросов с объектом [`Update`](https://dev.max.ru/docs-api/objects/Update), который содержит идентификатор изменённого комментария в поле `message.recipient.post_id`

   Когда кто-нибудь из подписчиков канала прокомментирует пост, через Webhook вам вернётся [`Update`](https://dev.max.ru/docs-api/objects/Update) с событием `comment_created` и текстом комментария в поле `body.text`.

**Пример запроса**
```bash
curl -X POST "https://platform-api2.max.ru/subscriptions" \
-H "Authorization: {access_token}" \
-H "Content-Type: application/json" \
-d '{
"url": "https://your-domain.com/webhook",
"update_types": ["comment_created", "comment_removed","comment_edited"],
"secret": "your_secret"
}'
```

4. **Проверьте, что комментарий соответствует вашим правилам модерации**

   Например, что в нём отсутствуют стоп-слова и ненормативная лексика. Правила модерации вы задаёте сами. Рекомендуем заранее ознакомить подписчиков с правилами канала

   Если комментарий нарушает правила, удалите его с помощью [`DELETE /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/DELETE/messages/-messageId-/comments)

   > После удаления комментарий восстановить нельзя

   При успешном удалении вам вернётся [`Update`](https://dev.max.ru/docs-api/objects/Update) с событием `comment_deleted`

 **Пример запроса**
```bash
curl -X DELETE "https://platform-api2.max.ru/comments/{commentId}" \
-H "Authorization: {access_token}" \
-H "Content-Type: application/json" \
```

5. Отправьте уведомление об удалении комментария и причинах. Это можно сделать с помощью [`POST /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/POST/messages/-messageId-/comments)

 **Пример запроса**
```bash
curl -X POST "https://platform-api2.max.ru/messages/{messageId}/comments" \
-H "Authorization: {access_token}" \
-H "Content-Type: application/json" \
-d '{
"text": "Комментарий был удалён за нарушение правил модерации канала",
}'
```
  

![ℹ️](/assets/emoji/information_2139-fe0f.png) Если у вас возникли вопросы, [посмотрите раздел с ответами](https://dev.max.ru/help)
