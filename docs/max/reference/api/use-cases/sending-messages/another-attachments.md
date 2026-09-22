<!-- source: https://dev.max.ru/docs-api/use-cases/sending-messages/another-attachments -->

# Отправка сообщений со стикерами и контактами

Для отправки сообщений в чаты и каналы в API используется метод [`POST` `/messages`](https://dev.max.ru/docs-api/methods/POST/messages)

Подробнее об отправке других типов вложения — [медиафайлы](https://dev.max.ru/docs-api/use-cases/sending-messages/media), [клавиатура](https://dev.max.ru/docs-api/use-cases/sending-messages/keyboard), [«Как отправить несколько медиафайлов»](https://dev.max.ru/docs-api/use-cases/sending-messages/media#%D0%9A%D0%B0%D0%BA%20%D0%BE%D1%82%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D1%82%D1%8C%20%D0%BD%D0%B5%D1%81%D0%BA%D0%BE%D0%BB%D1%8C%D0%BA%D0%BE%20%D0%BC%D0%B5%D0%B4%D0%B8%D0%B0%D1%84%D0%B0%D0%B9%D0%BB%D0%BE%D0%B2)

## Отправка стикера

Чтобы отправить сообщение cо стикером в чат или канала через API, используйте метод [`POST` `/messages`](https://dev.max.ru/docs-api/methods/POST/messages), в массиве `attachments` укажите `type = sticker`

Вы можете отправить стикер в сообщении или посте единственным вложением двумя способами:

- Через `code` — уникальный код стикера
- Через `url` стикера

В одном запросе можно отправить только один стикер

Стикер через code

Стикер через url

```json
{
"attachments": [
{
"type": "sticker",
"payload": {
// Уникальный код стикера
"code": "2fd04f94e"
}
}
]
}
```

## Отправка данных контакта

Чтобы отправить сообщение c контактом в чат или канала через API, используйте метод [`POST` `/messages`](https://dev.max.ru/docs-api/methods/POST/messages), в массиве `attachments` укажите `type = contact`

Вы можете отправить контакт в сообщении или посте единственным вложением или в комбинации с вложением одной кнопки `type=inline_keyboard`

Сам контакт можете отправить двумя способами:

- Через `contact_id` — идентификатор контакта
- Через `vcf_info` — информация о контакте в формате VCF

Контакт через contact\_id

Контакт через vcf\_info

Контакт + одна кнопка

```json
{
"text": "Это сообщение с данными контакта",
"attachments": [
{
// Вложение с контактом
"type": "contact",
"payload": {
// Имя контакта — поле необязательное
"name": "Имя Фамилия",
// Id контакта в MAX
"contact_id": "26575625762"
}
}
]
}
```

## Содержимое вкладок

_На сайте эти блоки показаны вкладками; здесь — все варианты, кроме уже показанного выше._

### Вкладка: Стикер через url

```json
{
"attachments": [
{
"type": "sticker",
"payload": {
// URL стикера
"url": "https://i.oneme.ru/getSmile?smileId=2fd04f94e&smileType=4"
}
}
]
}
```

### Вкладка: Контакт через vcf_info

```json
{
"text": "Это сообщение с данными контакта",
"attachments": [
{
// Вложение с контактом
"type": "contact",
"payload": {
// Имя контакта — поле необязательное
"name": "Имя Фамилия",
// vcf_info контакта в MAX
"vcf_info": "BEGIN:VCARD\r\nVERSION:3.0\r\nPRODID:ez-vcard 0.10.3\r\nTEL;TYPE=cell:7999999999\r\nFN:Имя Фамилиия\r\nEND:VCARD\r\n"
}
}
]
}
```

### Вкладка: Контакт + одна кнопка

```json
{
"attachments": [
{
"type": "contact",
"payload": {
// Имя контакта — поле необязательное
"name": "Имя Фамилия",
// vcf_info контакта в MAX 
"vcf_info": "BEGIN:VCARD\r\nVERSION:3.0\r\nPRODID:ez-vcard 0.10.3\r\nTEL;TYPE=cell:7999999999\r\nFN:Имя Фамилиия\r\nEND:VCARD\r\n"
}
},
// Вложение с кнопкой
{
"type": "inline_keyboard",
"payload": {
"buttons": [
[
{
// Тип кнопки
"type": "request_contact",
"text": "Запрос контакта"
}
]
]
}
}
]
}
```
