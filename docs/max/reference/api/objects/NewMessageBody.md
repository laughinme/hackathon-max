<!-- source: https://dev.max.ru/docs-api/objects/NewMessageBody -->

# NewMessageBody

Объект используется при отправке нового сообщения в чат или канал[`POST /messages`](https://dev.max.ru/docs-api/methods/POST/messages), редактировании существующего сообщения или поста [`PUT /messages`](https://dev.max.ru/docs-api/methods/PUT/messages), а также callback-отправке сообщения пользователю при нажатии им кнопки в чате или канале [`POST /answers`](https://dev.max.ru/docs-api/methods/POST/answers)

Параметры объекта содержат: текст и способ его форматирования, вложения, ссылку на связанное сообщение (ответ или пересылка), настройку PUSH-уведомлений для участников чата

`text`  
string  Nullable

до `4000` символов

`attachments`  
 AttachmentRequest[] Nullable

Вложения сообщения. Если поле пустое или равно `null`, изменений не произойдет. Если массив пуст, все вложения будут удалены

`link`  
object NewMessageLink Nullable

Ссылка на сообщение в чате или пост в канале. Ссылки на комментарии к постам в каналах не поддержаны

`notify`  
boolean  optional

По умолчанию: `true`

Если `false`, участники чата не получат push-уведомления. Для каналов необходимо отправлять запрос с `notify = true` или без этого поля, т.к. каналы не подразумевают отправку постов без push-уведомлений

`format`  
enum TextFormat Nullable optional

Возможные значения в enum: `"markdown"` `"html"`

Разметка текста сообщения. Подробнее — в разделе [Форматирование](https://dev.max.ru/docs-api/use-cases/sending-messages/text-formatting)

## Пример объекта

```json
{
 "text": "string",
  "attachments": [{ ... }],
  "link": { ... },
 "notify": true,
 "format": "markdown"
}
```
