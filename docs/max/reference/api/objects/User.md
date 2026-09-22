<!-- source: https://dev.max.ru/docs-api/objects/User -->

# User

Объект, описывающий один из вариантов наследования:

- [`User`](https://dev.max.ru/docs-api/objects/User) — объект содержит общую информацию о пользователе или боте без аватара
- [`UserWithPhoto`](https://dev.max.ru/docs-api/objects/UserWithPhoto) — объект с общей информацией о пользователе или боте, дополнительно содержит URL аватара и описание
- [`BotInfo`](https://dev.max.ru/docs-api/objects/BotInfo) — объект включает общую информацию о боте, URL аватара и описание. Дополнительно содержит список команд, поддерживаемых ботом. Возвращается только при вызове метода [`GET /me`](https://dev.max.ru/docs-api/methods/GET/me)
- [`ChatMember`](https://dev.max.ru/docs-api/objects/ChatMember) — объект включает общую информацию о пользователе или боте, URL аватара и описание при его наличии. Дополнительно содержит данные для пользователей-участников чата. Возвращается только при вызове некоторых методов группы `/chats`, например [`GET /chats/{chatId}/members`](https://dev.max.ru/docs-api/methods/GET/chats/-chatId-/members)

`user_id`  
integer  <int64>

Идентификатор пользователя или бота

`first_name`  
string

Отображаемое имя пользователя или бота

`last_name`  
string  Nullable optional

Отображаемая фамилия пользователя. Для ботов это поле не возвращается

`username`  
string  Nullable

Никнейм бота или уникальное публичное имя пользователя. В случае с пользователем может быть `null`, если тот недоступен или имя не задано

`is_bot`  
boolean

`true`, если это бот

`last_activity_time`  
integer  <int64>

Время последней активности пользователя или бота в MAX (Unix timestamp в миллисекундах). Если пользователь отключил в настройках профиля мессенджера MAX возможность видеть, что он в сети онлайн, поле может не возвращаться

`name`  
string  Nullable

*Устаревшее поле, скоро будет удалено*

## Пример объекта

```json
{
 "user_id": 0,
 "first_name": "string",
 "last_name": "string",
 "username": "string",
 "is_bot": true,
 "last_activity_time": 0,
 "name": "string"
}
```
