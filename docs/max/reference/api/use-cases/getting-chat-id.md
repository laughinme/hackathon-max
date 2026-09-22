<!-- source: https://dev.max.ru/docs-api/use-cases/getting-chat-id -->

# Получение chat\_id

`chat_id` — идентификатор чата или канала, в который добавлен бот. Он нужен большинству методов API, которые работают в контексте конкретного чата, например, чтобы отправить сообщение через метод [POST `/messages`](https://dev.max.ru/docs-api/methods/POST/messages) или закрепить пост через метод [PUT `/chats/{chatId}/pin`](https://dev.max.ru/docs-api/methods/PUT/chats/-chatId-/pin)

Сейчас API MAX не предоставляет готовой возможности для получения списка групповых чатов и каналов, в которые добавлен бот

В зависимости от типа объекта используйте подходящий способ получения `chat_id`:

| Тип объекта | Как получить chat\_id |
| --- | --- |
| Чат или канал | Только через подписку: [POST `/subscriptions`](https://dev.max.ru/docs-api/methods/POST/subscriptions) или [GET `/updates`](https://dev.max.ru/docs-api/methods/GET/updates)   `chat_id` придёт в объекте [Update](https://dev.max.ru/docs-api/objects/Update) на выбранные вами события – например, `bot_added` или `bot_started` |
| Мини-приложение | Либо через подписку (см. описание для чата и канала выше), либо на клиенте через [window.WebApp.initData](https://dev.max.ru/docs/webapps/bridge#window.WebApp.initData) библиотеки MAX Bridge |

  

![ℹ️](/assets/emoji/information_2139-fe0f.png) Если у вас возникли вопросы, [посмотрите раздел с ответами](https://dev.max.ru/help)
