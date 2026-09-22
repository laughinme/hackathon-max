<!-- source: https://dev.max.ru/docs-api/objects/CommentMessage -->

# CommentMessage

Комментарий в чате. Возвращается в ответ на запросы группы [`/comments`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments). В отличие от обычного сообщения в чате или канале не содержит вложений `attachments` и не поддерживает пересылку комментариев (поле `link.type = forward`)

`sender`  
object User optional

Пользователь, отправивший комментарий. Может быть `null`, если сообщение было опубликовано от имени канала

`recipient`  
object Recipient

Получатель сообщения: для комментариев — канал

`timestamp`  
integer  <int64>

Время создания сообщения в формате Unix timestamp в миллисекундах

`link`  
object CommentLinkedMessage Nullable optional

Комментарий, на который получен ответ

`body`  
object CommentMessageBody

Информация о комментарии

## Пример объекта

```json
{
  "sender": { ... },
  "recipient": { ... },
 "timestamp": 0,
  "link": { ... },
  "body": { ... }
}
```
