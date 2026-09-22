<!-- source: https://dev.max.ru/docs-api/methods/POST/messages/-messageId-/comments -->

# Отправка комментария

Для корректной работы ваших чат-ботов и мини-приложений направляйте запросы на домен `platform-api2.max.ru` вместо `platform-api.max.ru`. Также убедитесь, что добавили сертификат Минцифры в список доверенных

POST`/messages/{messageId}/comments`

Отправляет комментарий к посту в канале

Для этого:

• В настройках канала должны быть [включены комментарии](https://dev.max.ru/docs/channels/manage#%D0%9A%D0%B0%D0%BA%20%D0%B2%D0%BA%D0%BB%D1%8E%D1%87%D0%B8%D1%82%D1%8C%20%D0%BA%D0%BE%D0%BC%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%80%D0%B8%D0%B8%20%D0%B2%20%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB%D0%B5)  
• Бот, чей токен `access_token` используется для авторизации, должен быть администратором этого канала c правами `read_all_messages` и `write`

Чтобы получить информацию о правах бота, используйте [`GET /chats/-chatId-/members/admins`](https://dev.max.ru/docs-api/methods/GET/chats/-chatId-/members/admins). Подробнее о правах — в описании [`GET /chats/{chatId}/members/admins`](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members/admins#%D0%94%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%BD%D1%8B%D0%B5%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B0%20%D0%B0%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B0)

**Пример запроса**:

```bash
curl -X POST "https://platform-api2.max.ru/messages/{messageId}/comments" \
  -H "Authorization: {access_token}"
```

## Авторизация

`access_token`  
apiKey

> Передача токена через query-параметры больше не поддерживается — используйте заголовок `Authorization: <access_token>`

Токен для вызова HTTP-запросов присваивается при создании бота — его можно найти на [платформе](https://business.max.ru/self) в разделе **Чат-боты**. Выберите необходимого бота и нажмите **⋮** → **Настройки** → значок копирования справа от поля с токеном

Eсли вы верифицировали профиль и создали бота в [мини-приложении «MAX для бизнеса»](https://max.ru/business_bot?startapp), получить токен можно там же или в [боте «MAX для бизнеса»](https://max.ru/business_bot) с помощью команды **Получить токен**

Рекомендуем не разглашать токен посторонним, чтобы они не получили доступ к управлению ботом.
Токен может быть отозван за нарушение Правил платформы

## Параметры

`messageId`  
string    
(mid.)?[a-zA-Z0-9\_\-]+

Идентификатор сообщения (`mid`), к которому относится комментарий

## Тело запроса

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

## Результат

`message`  
object CommentMessage

Комментарий в чате. Возвращается в ответ на запросы группы [`/comments`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments). В отличие от обычного сообщения в чате или канале не содержит вложений `attachments` и не поддерживает пересылку комментариев (поле `link.type = forward`)

## Коды ответов

| Код | Описание |
| --- | --- |
| `200` | Возвращает информацию о созданном комментарии |
| `401` | Ошибка авторизации. Токен `access_token` указан некорректно или недействителен |
| `500` | Внутренняя ошибка сервера |
