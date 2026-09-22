<!-- source: https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments/-commentId- -->

# Получение комментария по его ID

Для корректной работы ваших чат-ботов и мини-приложений направляйте запросы на домен `platform-api2.max.ru` вместо `platform-api.max.ru`. Также убедитесь, что добавили сертификат Минцифры в список доверенных

GET`/messages/{messageId}/comments/{commentId}`

Возвращает информацию о комментарии к посту в канале по его идентификатору (`mid`)

Для этого бот, чей токен `access_token` используется для авторизации, должен быть администратором этого канала с правом `read_all_messages`

Чтобы получить информацию о правах бота, используйте [`GET /chats/-chatId-/members/admins`](https://dev.max.ru/docs-api/methods/GET/chats/-chatId-/members/admins). Подробнее о правах — в описании [`POST /chats/{chatId}/members/admins`](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members/admins#%D0%94%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%BD%D1%8B%D0%B5%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B0%20%D0%B0%D0%B4%D0%BC%D0%B8%D0%BD%D0%B8%D1%81%D1%82%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B0)

**Пример запроса**:

```bash
curl -X GET "https://platform-api2.max.ru/messages/{messageId}/comments/{commentId}" \
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

Идентификатор поста (`mid`), к которому относится комментарий

`commentId`  
string    
(mid.)?[a-zA-Z0-9\_\-]+

Идентификатор комментария (`mid`)

## Результат

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

## Коды ответов

| Код | Описание |
| --- | --- |
| `200` | Информация о комментарии, идентификатор которого был передан в запросе |
| `401` | Ошибка авторизации. Токен `access_token` указан некорректно или недействителен |
| `404` | Комментарий или пост не найдены, либо у бота нет к ним доступа. Проверьте, что бот назначен администратором канала с правом `read_all_messages` |
| `500` | Внутренняя ошибка сервера |
