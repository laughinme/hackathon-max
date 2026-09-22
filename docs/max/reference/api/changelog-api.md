<!-- source: https://dev.max.ru/docs-api/changelog-api -->

# История изменений API

> **Критически важные изменения**
>
> - С **19 июля 2026** для корректной работы чат-ботов и мини-приложений необходимо направлять запросы на домен `platform-api2.max.ru` вместо `platform-api.max.ru`, а также добавить сертификат Минцифры в список доверенных
> - Начиная **с июня 2026 года**, метод `GET /chats` больше не поддерживается. Вместо него для получения списка всех групповых чатов и каналов, в которые добавлен бот, используйте [POST /subscriptions](https://dev.max.ru/docs-api/methods/POST/subscriptions). Подробнее – на [странице «Получение списка всех групповых чатов и каналов»](https://dev.max.ru/docs-api/methods/GET/chats)

## Bots

Сентябрь 2026

#### Добавлено

- Теперь для работы с API MAX вы можете скачать спецификацию OpenAPI в формате `.YAML` [в репозитории на GitHub](https://github.com/max-messenger/api-schema). Подробнее — в разделе [«Спецификация OpenAPI»](https://dev.max.ru/docs-api#%D0%A1%D0%BF%D0%B5%D1%86%D0%B8%D1%84%D0%B8%D0%BA%D0%B0%D1%86%D0%B8%D1%8F%20OpenAPI)

Июль 2026

#### Добавлено

- Добавлен новый метод для редактирования, добавления и удаления команд бота [PATCH/me/commands](https://dev.max.ru/docs-api/methods/PATCH/me/commands)

## Chats

Сентябрь 2026

#### Изменено

- С 9 сентября 2026 работа метода [`POST /chats/{chatId}/members`](https://dev.max.ru/docs-api/methods/POST/chats/-chatId-/members) будет ограничена
Август 2026

#### Добавлено

- В метод [`PATCH /chats/{chatId}`](https://dev.max.ru/docs-api/methods/PATCH/chats/-chatId-) добавлен параметр `description` для изменения описания чата или канала
Июнь 2026

#### Удалено

- Метод [`GET /chats`](https://dev.max.ru/docs-api/methods/GET/chats) больше не поддерживается, и API не предоставляет готовой возможности для получения списка групповых чатов и каналов, в которые добавлен бот. Если вам требуется получить для бота такой список, используйте `POST /subscriptions` — подробнее в [статье](https://dev.max.ru/docs-api/methods/GET/chats)

## Сomments

Август 2026

#### Добавлено

- Добавили методы отправки, редактирования, получения и удаления комментариев к постам в каналах: [`POST /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/POST/messages/-messageId-/comments), [`GET /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments), [`GET /messages/{messageId}/comments/{commentId}`](https://dev.max.ru/docs-api/methods/GET/messages/-messageId-/comments/-commentId-), [`PUT /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/PUT/messages/-messageId-/comments), [`DELETE /messages/{messageId}/comments`](https://dev.max.ru/docs-api/methods/DELETE/messages/-messageId-/comments), а также события для работы с комментариями: `comment_created`, `comment_removed`,`comment_edited`

## Uploads

Июнь 2026

#### Изменено

- В методе `POST /uploads` добавлены [ограничения для видео (video), аудио (audio), изображений (image) и файлов (file)](https://dev.max.ru/docs-api/use-cases/sending-messages/media), отправляемых во вложении к сообщению

## Messages

Август 2026

#### Добавлено

- В метод [`POST /answers`](https://dev.max.ru/docs-api/methods/POST/answers#%D0%9F%D0%B0%D1%80%D0%B0%D0%BC%D0%B5%D1%82%D1%80%D1%8B) добавлен параметр `disable_link_preview`, который позволяет управлять отображением превью ссылок в сообщениях и постах

[Посмотреть историю изменений платформы MAX для партнёров](https://dev.max.ru/docs/changelog-platform)
