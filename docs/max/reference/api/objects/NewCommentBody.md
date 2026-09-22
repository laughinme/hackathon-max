<!-- source: https://dev.max.ru/docs-api/objects/NewCommentBody -->

# NewCommentBody

Объект используется при отправке нового комментария к посту в канале [`POST messages/-messageId-/comments`](https://dev.max.ru/docs-api/methods/POST/messages/-messageId-/comments) или редактировании старого [`PUT messages/-messageId-/comments`](https://dev.max.ru/docs-api/methods/PUT/messages/-messageId-/comments). В отличие от обычных сообщений в чатах и постов в каналах (объект [`NewMessageBody`](https://dev.max.ru/docs-api/objects/NewMessageBody)), в комментариях не поддерживаются вложения `attachments` и пересылка сообщения (тип `forward`)

`text`  
string  Nullable

до `4000` символов

Текст комментария

`link`  
object NewMessageLink Nullable

Ссылка на комментарий

`format`  
enum TextFormat Nullable optional

Возможные значения в enum: `"markdown"` `"html"`

Разметка текста комментария. Для комментариев не поддерживается упоминание других пользователей и гиперссылки. Подробнее — в разделе [Форматирование](https://dev.max.ru/docs-api/use-cases/sending-messages/text-formatting)

## Пример объекта

```json
{
 "text": "string",
  "link": { ... },
 "format": "markdown"
}
```
