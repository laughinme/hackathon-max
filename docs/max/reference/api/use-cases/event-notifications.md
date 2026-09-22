<!-- source: https://dev.max.ru/docs-api/use-cases/event-notifications -->

# Уведомления о событиях

> - Для повышения безопасности **с 25 мая 2026** прекращается поддержка получения вебхуков по HTTP, а также самоподписных сертификатов. Рекомендуем заранее перейти на HTTPS и сертификаты от доверенных центров, в том числе сертификаты Минцифры. Чтобы обновить подписку на события, используйте [POST /subscriptions](https://dev.max.ru/docs-api/methods/POST/subscriptions)
> - Получение обновлений с помощью [Long Polling](https://dev.max.ru/docs-api/methods/GET/updates) ограничено по скорости и сроку хранения событий — этот способ не подходит для production-окружения. Рекомендуем на всех этапах работы использовать [Webhook](https://dev.max.ru/docs-api/methods/POST/subscriptions)

API поддерживает два типа уведомлений о действиях пользователей с ботом — выбор зависит от этапа работы:

- Для **production-окружения — только Webhook**
- Для разработки и тестирования — Webhook или Long Polling

Использовать одновременно оба типа нельзя — выберите один из них

## Webhook

Чтобы получить обновления о событиях через Webhook, отправьте [POST-запрос `/subscriptions`](https://dev.max.ru/docs-api/methods/POST/subscriptions). В запросе укажите URL, на который должна приходить информация о новых событиях с ботом

Чтобы получить список всех подписок на обновления через Webhook, отправьте [GET-запрос `/subscriptions`](https://dev.max.ru/docs-api/methods/GET/subscriptions)

> - Для повышения безопасности **с 25 мая** прекращается поддержка получения вебхуков по HTTP, а также самоподписных сертификатов. Используйте HTTPS и сертификаты, выданные доверенным центром сертификации, в том числе сертификаты Минцифры. Подробнее о требованиях безопасности при подключении вебхуков — [в описании POST /subscriptions](https://dev.max.ru/docs-api/methods/POST/subscriptions)
> - Для стабильной работы ботов убедитесь, что максимальное количество запросов на `platform-api2.max.ru` — 30 rps

## Long Polling

> Получение обновлений с помощью [Long Polling](https://dev.max.ru/docs-api/methods/GET/updates) ограничено по скорости и сроку хранения событий — этот способ не подходит для production-окружения. Рекомендуем на всех этапах работы использовать [Webhook](https://dev.max.ru/docs-api/methods/POST/subscriptions)

Чтобы получить обновления через Long Polling, выполните [GET-запрос `/updates`](https://dev.max.ru/docs-api/methods/GET/updates)

  

![ℹ️](/assets/emoji/information_2139-fe0f.png) Если у вас возникли вопросы, [посмотрите раздел с ответами](https://dev.max.ru/help)
