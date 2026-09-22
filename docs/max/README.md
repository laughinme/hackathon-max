# docs/max — локальная документация MAX (боты и мини-приложения)

Снимок от **2026-09-22**. Источники: [dev.max.ru](https://dev.max.ru/docs), [max-messenger/api-schema](https://github.com/max-messenger/api-schema), [love-apples/maxapi](https://github.com/love-apples/maxapi).

**Начинать с [GUIDE.md](GUIDE.md)** — там собрано главное, нетривиальные ограничения и ссылки на детали.

## Что где лежит

| Путь | Что это |
|---|---|
| [GUIDE.md](GUIDE.md) | Гайд по разработке (написан вручную): ограничения, события, сообщения, клавиатуры, медиа, чаты и права, диплинки, мини-приложения, правила, Python-примеры, чек-лист |
| [openapi/SCHEMA.md](openapi/SCHEMA.md) | Справочник по всем эндпоинтам и **всем 133 типам** (включая варианты `Update`, вложения и кнопки), сгенерирован из схемы |
| [openapi/schema.yaml](openapi/schema.yaml) | Официальная OpenAPI 3.0-спецификация MAX Bot API (v0.0.33), годится для генерации клиента |
| [reference/api/](reference/api/) | Копия раздела [dev.max.ru/docs-api](https://dev.max.ru/docs-api): [обзор](reference/api/index.md), [changelog](reference/api/changelog-api.md), [методы](reference/api/methods/) (по файлу на метод: `VERB_path.md`), [объекты](reference/api/objects/), [сценарии](reference/api/use-cases/) (клавиатура, медиа, форматирование, chat_id, команды, комментарии) |
| [reference/platform/](reference/platform/) | Копия раздела [dev.max.ru/docs](https://dev.max.ru/docs): [мини-приложения](reference/platform/webapps/) (подключение, **MAX Bridge**, валидация), [чат-боты](reference/platform/chatbots/) (создание, модерация, JS и Go SDK, примеры), [каналы](reference/platform/channels/), [Цифровой ID](reference/platform/digital-id.md), [правовые документы](reference/platform/legal/), [changelog платформы](reference/platform/changelog-platform.md) |
| [reference/faq/](reference/faq/) | Копия FAQ [dev.max.ru/help](https://dev.max.ru/help) |
| [python-maxapi/](python-maxapi/) | Документация ([docs/](python-maxapi/docs/)) и 15 примеров ([examples/](python-maxapi/examples/)) Python-библиотеки `maxapi` (коммит в `SOURCE_COMMIT`) |
| [certs/russiantrustedca.pem](certs/russiantrustedca.pem) | CA Минцифры (Russian Trusted Sub CA). Нужен для TLS к `platform-api2.max.ru` из Python без `maxapi` |
| [scripts/update_docs.py](scripts/update_docs.py) | Заново скачивает всё выше и пересобирает `SCHEMA.md` |
| [scripts/gen_schema_md.py](scripts/gen_schema_md.py) | Генератор `openapi/SCHEMA.md` из `schema.yaml` |

Каждый файл в `reference/` начинается с `<!-- source: URL -->` — это ссылка на оригинал. Если на сайте часть контента была во вкладках (примеры на других языках, варианты), она дописана в конец файла разделом «Содержимое вкладок».

## Как искать

```bash
grep -rn "attachment.not.ready" docs/max/          # по всему снимку
grep -n "^### MessageCallbackUpdate" -A12 docs/max/openapi/SCHEMA.md   # тип целиком
ls docs/max/reference/api/methods/                 # все методы API
```

## Обновление

```bash
uv run --with markdownify --with beautifulsoup4 --with pyyaml python docs/max/scripts/update_docs.py
```

После обновления просмотрите changelog-и и при необходимости поправьте `GUIDE.md`: он не генерируется.
