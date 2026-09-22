<!-- source: https://dev.max.ru/docs-api/use-cases/sending-messages/attachment-types -->

# Типы вложений

Для отправки сообщений в чаты и каналы в API используется метод [`POST` `/messages`](https://dev.max.ru/docs-api/methods/POST/messages)

Помимо текста сообщения могут содержать вложения, которые передаются в объекте `attachments` запроса [`POST` `/messages`](https://dev.max.ru/docs-api/methods/POST/messages)

Вложения могут быть одного из типов `type`:

| Тип | Описание и ограничения |
| --- | --- |
| `image` | Изображения   Доступные форматы: JPG, JPEG, PNG, GIF, TIFF, BMP, HEIC   Максимальный размер одного изображения: до 50 МБ или не более 7680 × 7680 px — должны выполняться оба критерия. Например, отправить изображение 55 МБ и 7600 × 7600 px нельзя |
| `video` | Видеофайлы   Доступные форматы: MP4, MOV, MKV, WEBM   Максимальный размер одного видео: до 250 МБ |
| `audio` | Аудиофайлы   Доступные форматы: MP3, WAV, M4A и другие   Максимальный размер одного аудио: до 256 МБ или длительностью не более 60 мин — должны выполняться оба критерия. Например, отправить аудио размером 250 МБ и длительностью 70 минут нельзя |
| `file` | Другие медиафайлы   Максимальный размер одного файла: до 4 ГБ   Доступные форматы: TXT, DOC, PDF и другие распространённые форматы |
| `sticker` | Стикеры |
| `inline_keyboard` | Кнопки клавиатуры   Максимальное количество: `210` кнопок, сгруппированных в `30` рядов — до `7` кнопок в каждом (до 3, если это кнопки типа `link`, `open_app`, `request_geo_location` или [`request_contact`](https://dev.max.ru/docs-api/use-cases/sending-messages/keyboard#%D0%9A%D0%BD%D0%BE%D0%BF%D0%BA%D0%B0%20request_contact)) |
| `location` | Геолокация |
| `share` | Медиафайлы с превью |
| `contact` | Контактные данные |

Подробнее об отправке разных типов вложения — [медиафайлы](https://dev.max.ru/docs-api/use-cases/sending-messages/media), [клавиатура](https://dev.max.ru/docs-api/use-cases/sending-messages/keyboard), [стикеры и контакты](https://dev.max.ru/docs-api/use-cases/sending-messages/another-attachments)
