# MAX Bot API — OpenAPI reference (v0.0.33)

_Generated from `schema.yaml` by `scripts/gen_schema_md.py` — do not edit by hand._

Base URL: `https://platform-api2.max.ru`, auth header `Authorization: <access_token>`.

## Endpoints

### GET `/me`

**Get current bot info**

Returns info about current bot. Current bot can be identified by access token. Method returns bot identifier, name and avatar (if any)

- `200` Bot info → [BotInfo](#botinfo)
- `401` 
- `500` 

### PATCH `/me/commands`

**Edit current bot commands**

Edits current bot Commands.

Body: [BotCommandsPatch](#botcommandspatch)

- `200` Modified bot commands info → [BotCommandsInfo](#botcommandsinfo)
- `401` 
- `500` 

### GET `/chats/{chatId}`

**Get chat**

Returns info about chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Requested chat or channel identifier |

- `200` Chat or channel information → [Chat](#chat)
- `401` 
- `500` 

### PATCH `/chats/{chatId}`

**Edit chat or channel info**

Edits chat or channel info: title, icon, etc…

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |

Body: [ChatPatch](#chatpatch)

- `200` If success, returns updated chat object → [Chat](#chat)
- `401` 
- `403` 
- `500` 

### POST `/chats/{chatId}/actions`

**Send action**

Send bot action to chat.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat identifier |

Body: [ActionRequestBody](#actionrequestbody)

- `200` 
- `401` 
- `500` 

### GET `/chats/{chatId}/pin`

**Get pinned message**

Get pinned message in chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat identifier to get its pinned message |

- `200` Pinned message → [GetPinnedMessageResult](#getpinnedmessageresult)
- `401` 
- `403` 
- `404` 
- `500` 

### PUT `/chats/{chatId}/pin`

**Pin message**

Pins message in chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat identifier where message should be pinned |

Body: [PinMessageBody](#pinmessagebody)

- `200` 
- `401` 
- `403` 
- `404` 
- `500` 

### DELETE `/chats/{chatId}/pin`

**Unpin message**

Unpins message in chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat identifier to remove pinned message |

- `200` 
- `401` 
- `403` 
- `404` 
- `500` 

### GET `/chats/{chatId}/members/me`

**Get chat or channel membership**

Returns chat or channel membership info for current bot

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |

- `200` Current bot membership info → [ChatMember](#chatmember)
- `401` 
- `403` 
- `404` 
- `500` 

### DELETE `/chats/{chatId}/members/me`

**Leave chat**

Removes bot from chat or channel members.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |

- `200` 
- `401` 
- `403` 
- `404` 
- `500` 

### GET `/chats/{chatId}/members/admins`

**Get chat or channel admins**

Returns all chat or channel administrators. Bot must be **administrator** in requested chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |

- `200` Administrators list → [ChatMembersList](#chatmemberslist)
- `401` 
- `403` 
- `404` 
- `500` 

### POST `/chats/{chatId}/members/admins`

**Set chat or channel admins**

Returns true if all administrators added. Additional permissions may require

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |

Body: [ChatAdminsList](#chatadminslist)

- `200` 
- `401` 
- `403` 
- `404` 
- `500` 

### DELETE `/chats/{chatId}/members/admins/{userId}`

**Revoke admin rights**

Revokes admin rights from a user in the chat or channel by removing their administrative privileges. Additional permissions may require.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |
| `userId` | path | [UserId](#userid) | ✓ |  | User identifier |

- `200` 
- `401` 
- `500` 

### GET `/chats/{chatId}/members`

**Get members**

Returns users participated in chat or channel.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |
| `user_ids` | query | [UserId](#userid)[] |  | nullable | Comma-separated list of users identifiers to get their membership. When this parameter is passed, both `count` and `marker` are ignored |
| `marker` | query | integer <int64> |  |  | Marker |
| `count` | query | integer |  | minimum=1, maximum=100, default=20 | Count |

- `200` Returns members list and pointer to the next data page → [ChatMembersList](#chatmemberslist)
- `401` 
- `403` 
- `404` 
- `500` 

### POST `/chats/{chatId}/members`

**Add members**

Adds members to chat. Additional permissions may require.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat identifier |

Body: [UserIdsList](#useridslist)

- `200` Result of chat members modification request → [ModifyMembersResult](#modifymembersresult)
- `401` 
- `403` 
- `404` 
- `500` 

### DELETE `/chats/{chatId}/members`

**Remove member**

Removes member from chat or channel. Additional permissions may require.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chatId` | path | [ChatId](#chatid) | ✓ |  | Chat or channel identifier |
| `user_id` | query | [UserId](#userid) | ✓ |  | User id to remove from chat or channel |
| `block` | query | boolean |  | default=False | Set to `true` if user should be blocked in chat. Applicable only for chats that have public or private link. Ignored otherwise |

- `200` 
- `401` 
- `403` 
- `500` 

### GET `/subscriptions`

**Get subscriptions**

In case your bot gets data via WebHook, the method returns list of all subscriptions

- `200` As expected → [GetSubscriptionsResult](#getsubscriptionsresult)
- `401` 
- `500` 

### POST `/subscriptions`

**Subscribe**

Subscribes bot to receive updates via WebHook. After calling this method, the bot will receive notifications about new events in chat rooms at the specified URL. Your server **must** be listening on port **443**

Body: [SubscriptionRequestBody](#subscriptionrequestbody)

- `200` 
- `401` 
- `500` 

### DELETE `/subscriptions`

**Unsubscribe**

Unsubscribes bot from receiving updates via WebHook. After calling the method, the bot stops receiving notifications about new events. Notification via the long-poll API becomes available for the bot. Receiving updates via Long Polling is limited in speed and event retention time — this method is not suitable for production environments. We recommend using Webhook at all stages of work

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `url` | query | string | ✓ |  | URL to remove from WebHook subscriptions |

- `200` 
- `401` 
- `500` 

### POST `/uploads`

**Get upload URL**

Returns the URL for the subsequent file upload. For example, you can upload it via curl: ```curl -i -X POST -H "Content-Type: multipart/form-data" -F "data=@movie.mp4" "%UPLOAD_URL%"``` Two types of an upload are supported: - single request upload (multipart request) - and resumable upload. ##### Multipart upload This type of upload is a simpler one but it is less reliable and agile. If a `Content-Type`: multipart/form-data header is passed in a request our service indicates upload type as a simple single request upload. This type of an upload has some restrictions: - image — available formats: JPG, JPEG, PNG, GIF, TIFF, BMP, HEIC; maximum size for a single image: up to 50 MB AND no more than 7680 x 7680 px — both criteria must be met. For example, you cannot upload an image that is 55 MB and has dimensions of 7600 x 7600 px. - video — available formats: MP4, MOV, MKV, WEBM; maximum size for a single video: up to 250 MB - audio — available formats: MP3, WAV, M4A, and others, maximum size for a single audio file: up to 256 MB OR duration of no more than 60 minutes — both criteria must be met. For example, you cannot send an audio file that is 250 MB and 70 minutes long. - file — available formats: TXT, DOC, PDF, and other common formats, maximum size for a single file: up to 4 GB - type=photo parameter is no longer supported. If you used type=photo in previously created integrations, please replace it with type=image - Only one mediafile per request can be uploaded - No possib

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `type` | query | [UploadType](#uploadtype) | ✓ |  | Uploaded file type: image, audio, video, file |

- `200` Returns URL to upload attachment → [UploadEndpoint](#uploadendpoint)
- `401` 
- `500` 

### GET `/messages`

**Get messages**

Returns messages in chat or channel: result page and marker referencing to the next page. Messages traversed in reverse direction so the latest message in chat will be first in result array. Therefore if you use `from` and `to` parameters, `to` must be **less than** `from`

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `chat_id` | query | [ChatId](#chatid) |  |  | Chat or channel identifier to get messages in chat or channel |
| `message_ids` | query | object |  | nullable | Comma-separated list of message ids to get |
| `from` | query | [bigint](#bigint) |  |  | Start time for requested messages - use after instead |
| `to` | query | [bigint](#bigint) |  |  | End time for requested messages - use before instead |
| `before` | query | integer <int64> |  | minimum=0 | Messages before timestamp |
| `after` | query | integer <int64> |  | minimum=0 | Messages after timestamp |
| `count` | query | integer <int32> |  | minimum=1, maximum=100, default=50 | Maximum amount of messages in response |

- `200` Returns list of messages → [MessageList](#messagelist)
- `401` 
- `403` This exception happens when user suspended bot or it doesn't have access to chat → [Error](#error)
- `500` 

### POST `/messages`

**Send message**

Sends a message to a chat, channel or dialog. As a result for this method new message identifier returns. In the case of a channel, it returns an error if you pass notify=false ### Attaching media Attaching media to messages is a three-step process. At first step, you should obtain a URL to upload your media files. At the second, you should upload binary of appropriate format to URL you obtained at the previous step. See [upload section](https://dev.max.ru/docs-api/methods/POST/uploads) in docs for details. Finally, if the upload process was successful, you will receive JSON-object in a response body. Use this object to create attachment. Construct an object with two properties: - `type` with the value set to appropriate media type - and `payload` filled with the JSON you've got. For example, you can attach a video to message this way: 1. Get URL to upload. Execute following: ```shell curl -X POST 'https://platform-api2.max.ru/uploads?type=video' -H 'Authorization: %access_token%' ``` As the result it will return URL for the next step. ```json { "url": "http://omub.okcdn.ru/upload.do…" } ``` 2. Use this url to upload your binary: ```shell curl -i -X POST -H "Content-Type: multipart/form-data" -F "data=@movie.mp4" "http://omub.okcdn.ru/upload.do…" ``` As the result it will return JSON you can attach to message: ```json { "token": "_3Rarhcf1PtlMXy8jpgie8Ai_KARnVFYNQTtmIRWNh4" } ``` 3. Send message with attach: ```json { "text": "Message with video", "attachments": [ { "type": "

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `user_id` | query | [UserId](#userid) |  |  | Fill this parameter if you want to send message to user |
| `chat_id` | query | [ChatId](#chatid) |  |  | Fill this if you send message to chat or channel |
| `disable_link_preview` | query | boolean |  | default=False | If `false`, server will not generate media preview for links in text |

Body: [NewMessageBody](#newmessagebody)

- `200` Returns info about created message → [SendMessageResult](#sendmessageresult)
- `401` 
- `403` This exception happens when user suspended bot, bot doesn't have access to chat or channel or forwarded message is prohibited → [Error](#error)
- `500` 

### PUT `/messages`

**Edit message**

Updated message should be sent as `NewMessageBody` in a request body. In case `attachments` field is `null`, the current message attachments won’t be changed. In case of sending an empty list in this field, all attachments will be deleted.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `message_id` | query | [MessageId](#messageid) | ✓ |  | Editing message identifier |

Body: [NewMessageBody](#newmessagebody)

- `200` 
- `401` 
- `500` 

### DELETE `/messages`

**Delete message**

Deletes message in a dialog, chat or channel if bot has permission to delete messages.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `message_id` | query | [MessageId](#messageid) | ✓ |  | Deleting message identifier |

- `200` 
- `401` 
- `403` 
- `500` 

### GET `/messages/{messageId}`

**Get message**

Returns single message by its identifier.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) to get single message in chat or channel |

- `200` Returns single message → [Message](#message)
- `401` 
- `404` In case when message is not found or bot has no access to it → [Error](#error)
- `500` 

### GET `/messages/{messageId}/comments`

**Get comments**

Returns comments for a message in channel: result page and marker referencing to the next page. Comments traversed in reverse direction so the latest comment for the message will be first in result array. Additional permissions may require

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) of the commented message |
| `comment_ids` | query | object |  | nullable | Comma-separated list of comment ids to get |
| `before` | query | integer <int64> |  | minimum=0 | Comments before timestamp |
| `after` | query | integer <int64> |  | minimum=0 | Comments after timestamp |
| `count` | query | integer <int32> |  | minimum=1, maximum=100, default=50 | Maximum amount of comments in response |

- `200` Returns list of comments → [CommentMessageList](#commentmessagelist)
- `401` 
- `500` 

### POST `/messages/{messageId}/comments`

**Send comment**

Sends a comment to a message in channel. Attachments are not allowed in comments. Additional permissions may require

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) of the commented message |
| `disable_link_preview` | query | boolean |  | default=False | If `false`, server will not generate media preview for links in text |

Body: [NewCommentBody](#newcommentbody)

- `200` Returns info about created comment → [SendCommentResult](#sendcommentresult)
- `401` 
- `500` 

### PUT `/messages/{messageId}/comments`

**Edit comment**

Updated comment should be sent as `NewCommentBody` in a request body. Attachments are not allowed in comments. Additional permissions may require

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) of the commented message |
| `comment_id` | query | [MessageId](#messageid) | ✓ |  | Editing comment identifier |

Body: [NewCommentBody](#newcommentbody)

- `200` 
- `401` 
- `500` 

### DELETE `/messages/{messageId}/comments`

**Delete comment**

Deletes comment for a message in channel if bot has permission to delete messages.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) of the commented message |
| `comment_id` | query | [MessageId](#messageid) | ✓ |  | Deleting comment identifier |

- `200` 
- `401` 
- `403` 
- `500` 

### GET `/messages/{messageId}/comments/{commentId}`

**Get comment**

Returns single comment by its identifier. Additional permissions may require

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `messageId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Message identifier (`mid`) of the commented message |
| `commentId` | path | [MessageId](#messageid) | ✓ | pattern='(mid.)?[a-zA-Z0-9_\\-]+' | Comment identifier (`mid`) to get single comment in channel |

- `200` Returns single comment → [CommentMessage](#commentmessage)
- `401` 
- `404` In case when comment or message is not found or bot has no access to it → [Error](#error)
- `500` 

### GET `/videos/{videoToken}`

**Get video details**

Returns detailed information about video attachment: playback URLs and additional metadata.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `videoToken` | path | string | ✓ | pattern='[\\w-]+' | Video attachment token |

- `200` Detailed video attachment info → [VideoAttachmentDetails](#videoattachmentdetails)
- `401` 
- `403` 
- `404` In case when message is not found or bot has no access to it → [Error](#error)
- `500` 

### POST `/answers`

**Answer on callback**

This method should be called to send an answer after a user has clicked the button. The answer may be an updated message or/and a one-time user notification.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `callback_id` | query | string | ✓ | minLength=1, pattern='^\\s*\\S[\\s\\S]*$' | Identifies a button clicked by user. Bot receives this identifier after user pressed button as part of `MessageCallbackUpdate` |
| `disable_link_preview` | query | boolean |  | default=False | If `true`, server will not generate media preview for links in updated message text |

Body: [CallbackAnswer](#callbackanswer)

- `200` 
- `401` 
- `405` 
- `500` 

### GET `/updates`

**Get updates**

Receiving updates via Long Polling is limited in speed and event retention time — this method is not suitable for production environments. We recommend using Webhook at all stages of work. You can use this method for getting updates in case your bot is not subscribed to WebHook. The method is based on long polling. Every update has its own sequence number. `marker` property in response points to the next upcoming update. All previous updates are considered as *committed* after passing `marker` parameter. If `marker` parameter is **not passed**, your bot will get all updates happened after the last commitment.

| Param | In | Type | Req | Constraints | Description |
|---|---|---|---|---|---|
| `limit` | query | integer |  | minimum=1, maximum=1000, default=100 | Maximum number of updates to be retrieved |
| `timeout` | query | integer |  | minimum=0, maximum=90, default=30 | Timeout in seconds for long polling |
| `marker` | query | integer <int64> |  | nullable | Pass `null` to get updates you didn't get yet |
| `types` | query | string[] |  | nullable | Comma separated list of update types your bot want to receive |

- `200` List of updates → [UpdateList](#updatelist)
- `401` 
- `405` 
- `500` 

## Schemas

### bigint

64-bit integer identifier

Type: integer <int64> 

### UserId

User identifier

Type: integer <int64> 

### ChatId

Chat identifier

Type: integer <int64> 

### MessageId

Message identifier

Type: string minLength=1

### Url

URL string

Type: string 

### SubscriptionUrl

URL of HTTPS-endpoint of your bot. Must starts with https://

Type: string 

### User

User object

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `user_id` | [UserId](#userid) | ✓ |  | Users identifier |
| `first_name` | string | ✓ |  | Users first name |
| `last_name` | string |  | nullable | Users last name |
| `username` | string |  | nullable | Unique public user name. Can be `null` if user is not accessible or it is not set |
| `is_bot` | boolean | ✓ |  | `true` if user is bot |
| `last_activity_time` | integer <int64> |  | nullable | Time of last user activity in Max (Unix timestamp in milliseconds). Can be outdated if user disabled its "online" status in settings |

### UserWithPhoto

User with description and avatar URLs

Extends: [User](#user)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `description` | string |  | maxLength=16000, nullable | User description. Can be `null` if user did not fill it out |
| `avatar_url` | string |  | nullable | URL of avatar |
| `full_avatar_url` | string |  | nullable | URL of avatar of a bigger size |

### BotInfo

Bot information with commands and official status

Extends: [UserWithPhoto](#userwithphoto)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `commands` | [BotCommand](#botcommand)[] |  | maxItems=32, nullable | Commands supported by bot |

### BotCommandsInfo

Bot commands information

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `commands` | [BotCommand](#botcommand)[] |  | maxItems=32, nullable | Commands supported by bot |

### BotCommandsPatch

Patch object for updating bot commands

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `commands` | [BotCommand](#botcommand)[] |  | maxItems=32 | Commands supported by bot |

### BotCommand

Bot command with name and description

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `name` | string | ✓ | minLength=1, maxLength=64 | Command name |
| `description` | string |  | minLength=1, maxLength=128, nullable | Optional command description |

### Chat

Chat, channel or dialog object

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chats identifier |
| `type` | [ChatType](#chattype) | ✓ |  | Type of chat. One of: dialog, chat, channel |
| `status` | [ChatStatus](#chatstatus) | ✓ |  | Chat status. One of: - active: bot is active member of chat - removed: bot was kicked - left: bot intentionally left chat - closed: chat was closed - suspended: bot was stopped by user. *Only for dialogs* |
| `title` | string |  | nullable | Visible title of chat. Can be null for dialogs |
| `icon` | [Image](#image) |  | nullable | Icon of chat |
| `last_event_time` | integer <int64> | ✓ |  | Time of last event occurred in chat |
| `participants_count` | integer <int32> | ✓ |  | Number of people in chat. Always 2 for `dialog` chat type |
| `owner_id` | [UserId](#userid) |  | nullable | Identifier of chat owner. Visible only for chat admins |
| `participants` | object |  | nullable | Participants in chat with time of last activity. Can be *null* when you request list of chats. Visible for chat admins only |
| `is_public` | boolean | ✓ |  | Is current chat publicly available. Always `false` for dialogs |
| `link` | string |  | nullable | Link on chat |
| `description` | string |  | nullable | Chat description |
| `dialog_with_user` | [UserWithPhoto](#userwithphoto) |  | nullable | Another user in conversation. For `dialog` type chats only |
| `messages_count` | integer |  | nullable | Messages count in chat. Only for group chats and channels. **Not available** for dialogs |
| `pinned_message` | [Message](#message) |  | nullable | Pinned message in chat or channel. Returned only when single chat is requested |

### ChatType

Type of chat. Dialog (one-on-one), chat or channel

Values: `dialog`, `chat`, `channel`

### ChatStatus

Chat status for current bot

Values: `active`, `removed`, `left`, `closed`, `suspended`

### ChatList

Paginated list of chats

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chats` | [Chat](#chat)[] | ✓ |  | List of requested chats |
| `marker` | integer <int64> |  | nullable | Reference to the next page of requested chats |

### ChatPatch

Patch object for updating chat info

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `icon` | [PhotoAttachmentRequestPayload](#photoattachmentrequestpayload) |  | nullable |  |
| `title` | string |  | minLength=1, maxLength=200, nullable |  |
| `description` | string |  | maxLength=16000, nullable | Chat description up to 16k characters long. Pass empty string to remove description |
| `pin` | string |  | nullable | Identifier of message to be pinned in chat. In case you want to remove pin, use /unpin method |
| `notify` | boolean |  | default=True, nullable | By default, participants will be notified about change with system message in chat/channel |

### ChatMember

Chat or channel member with membership info

Extends: [UserWithPhoto](#userwithphoto)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `last_access_time` | integer <int64> | ✓ |  | User last activity time in chat or channel . Can be outdated for super chats and channels (equals to `join_time`) |
| `is_owner` | boolean | ✓ |  |  |
| `is_admin` | boolean | ✓ |  |  |
| `join_time` | integer <int64> | ✓ |  |  |
| `permissions` | [ChatAdminPermission](#chatadminpermission)[] |  | nullable | Permissions in chat if member is admin. `null` otherwise |
| `alias` | string |  | nullable | Alias in chat if member is admin. By default, `null` |

### ChatAdminPermission

Chat admin permissions

Values: `read_all_messages`, `add_remove_members`, `add_admins`, `change_chat_info`, `pin_message`, `edit_link`, `write`, `edit`, `delete`, `can_call`, `view_stats`

### ChatMembersList

Paginated list of chat members

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `members` | [ChatMember](#chatmember)[] | ✓ |  | Participants in chat with time of last activity |
| `marker` | integer <int64> |  | nullable | Pointer to the next data page |

### Image

Generic schema describing image object

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ |  | URL of image |

### Subscription

Schema to describe WebHook subscription

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ |  | Webhook URL |
| `time` | integer <int64> | ✓ |  | Unix-time when subscription was created |
| `update_types` | string[] |  | nullable | Update types bot subscribed for |

### Recipient

New message recipient. Could be user, chat or channel

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) |  | nullable | Chat or channel identifier |
| `chat_type` | [ChatType](#chattype) | ✓ |  | Chat type |
| `user_id` | [UserId](#userid) |  | nullable | User identifier, if message was sent to user |
| `post_id` | [MessageId](#messageid) |  | nullable | Post identifier for comments |

### Message

Message in chat

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `sender` | [User](#user) |  | nullable | User who sent this message. Can be `null` if message has been posted on behalf of a channel |
| `recipient` | [Recipient](#recipient) | ✓ |  | Message recipient. Could be user, chat or channel |
| `timestamp` | integer <int64> | ✓ |  | Unix-time when message was created |
| `link` | [LinkedMessage](#linkedmessage) |  | nullable | Forwarded or replied message |
| `body` | [MessageBody](#messagebody) | ✓ |  | Body of created message. Text + attachments. Could be null if message contains only forwarded message |
| `stat` | [MessageStat](#messagestat) |  | nullable | Message statistics. Available only for channels in getMessages method context |
| `url` | string |  | nullable | Message public URL. Can be `null` for dialogs or non-public chats/channels |

### CommentMessage

Comment message in chat. Unlike Message, has no public url and body has no attachments.

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `sender` | [User](#user) |  | nullable | User who sent this comment. Can be `null` if message has been posted on behalf of a channel |
| `recipient` | [Recipient](#recipient) | ✓ |  | Message recipient. Could be user or chat, for comments - only channel |
| `timestamp` | integer <int64> | ✓ |  | Unix-time when message was created |
| `link` | [CommentLinkedMessage](#commentlinkedmessage) |  | nullable | Forwarded or replied message |
| `body` | [CommentMessageBody](#commentmessagebody) | ✓ |  | Body of created comment. Text only, no attachments. |
| `stat` | [MessageStat](#messagestat) |  | nullable | Message statistics. Available only for channels in in getMessages method context |

### MessageStat

Message statistics

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `views` | integer | ✓ |  |  |

### MessageBody

Schema representing body of message

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `mid` | [MessageId](#messageid) | ✓ |  | Unique identifier of message |
| `seq` | integer <int64> | ✓ |  | Sequence identifier of message in chat |
| `text` | string |  | nullable | Message text |
| `attachments` | [Attachment](#attachment)[] |  | nullable | Message attachments. Could be one of `Attachment` type. See description of this schema |
| `markup` | [MarkupElement](#markupelement)[] |  | nullable | Message text markup. See formatting section in https://dev.max.ru/docs-api for more info |

### CommentMessageBody

Schema representing body of a comment message. Unlike MessageBody, attachments are not allowed.

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `mid` | [MessageId](#messageid) | ✓ |  | Unique identifier of message |
| `seq` | integer <int64> | ✓ |  | Sequence identifier of message in chat |
| `text` | string |  | nullable | Message text |
| `markup` | [MarkupElement](#markupelement)[] |  | nullable | Message text markup. See Formatting section in https://dev.max.ru/docs-api for more info |

### MessageList

Paginated list of messages

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `messages` | [Message](#message)[] | ✓ |  | List of messages |

### CommentMessageList

Paginated list of comment messages

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `messages` | [CommentMessage](#commentmessage)[] | ✓ |  | List of comment messages |

### TextFormat

Message text format

Values: `markdown`, `html`

### NewMessageBody

Body of a new message to send

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `text` | string |  | maxLength=4000, nullable | Message text |
| `attachments` | [AttachmentRequest](#attachmentrequest)[] |  | nullable | Message attachments. See `AttachmentRequest` and it's inheritors for full information |
| `link` | [NewMessageLink](#newmessagelink) |  | nullable | Link to Message |
| `notify` | boolean |  | default=True | If false, chat participants would not be notified |
| `format` | [TextFormat](#textformat) |  | nullable | If set, message text will be formatted according to given markup |

### NewCommentBody

Body of a new comment to send. Unlike NewMessageBody, attachments are not allowed.

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `text` | string |  | maxLength=4000, nullable | Message text |
| `link` | [NewMessageLink](#newmessagelink) |  | nullable | Link to Message |
| `format` | [TextFormat](#textformat) |  | nullable | If set, message text will be formatted according to given markup |

### NewMessageLink

Link to a message for reply or forward

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | [MessageLinkType](#messagelinktype) | ✓ |  | Type of message link |
| `mid` | [MessageId](#messageid) | ✓ |  | Message identifier of original message |

### LinkedMessage

Forwarded or replied message

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | [MessageLinkType](#messagelinktype) | ✓ |  | Type of linked message |
| `sender` | [User](#user) |  | nullable | User sent this message. Can be `null` if message has been posted on behalf of a channel |
| `chat_id` | [ChatId](#chatid) |  |  | Chat where message has been originally posted |
| `message` | [MessageBody](#messagebody) | ✓ |  |  |

### CommentLinkedMessage

Forwarded or replied comment. Unlike LinkedMessage, `message` is a CommentMessageBody (no attachments, as comments cannot have them)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | [MessageLinkType](#messagelinktype) | ✓ |  | Type of linked message |
| `sender` | [User](#user) |  | nullable | User sent this message. Can be `null` if message has been posted on behalf of a channel |
| `chat_id` | [ChatId](#chatid) |  |  | Chat where message has been originally posted |
| `message` | [CommentMessageBody](#commentmessagebody) | ✓ |  |  |

### SendMessageResult

Result of sending a message

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) | ✓ |  |  |

### SendCommentResult

Result of sending a comment

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [CommentMessage](#commentmessage) | ✓ |  |  |

### Attachment

Generic schema representing message attachment

Discriminator `type`:
- `image` → [PhotoAttachment](#photoattachment)
- `video` → [VideoAttachment](#videoattachment)
- `audio` → [AudioAttachment](#audioattachment)
- `file` → [FileAttachment](#fileattachment)
- `sticker` → [StickerAttachment](#stickerattachment)
- `contact` → [ContactAttachment](#contactattachment)
- `inline_keyboard` → [InlineKeyboardAttachment](#inlinekeyboardattachment)
- `share` → [ShareAttachment](#shareattachment)
- `location` → [LocationAttachment](#locationattachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | string | ✓ |  |  |

### PhotoAttachment

Image attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [PhotoAttachmentPayload](#photoattachmentpayload) | ✓ |  |  |

### PhotoAttachmentPayload

Payload of photo attachment containing image metadata

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `photo_id` | integer <int64> | ✓ |  | Unique identifier of this image |
| `token` | string | ✓ |  |  |
| `url` | string | ✓ |  | Image URL |

### VideoAttachment

Video attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [MediaAttachmentPayload](#mediaattachmentpayload) | ✓ |  |  |
| `thumbnail` | [VideoThumbnail](#videothumbnail) |  | nullable | Video thumbnail |
| `width` | integer |  | nullable | Video width |
| `height` | integer |  | nullable | Video height |
| `duration` | integer |  | nullable | Video duration in seconds |

### VideoThumbnail

Video thumbnail image

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ |  | Image URL |

### VideoUrls

Available video download and streaming URLs by resolution

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `mp4_1080` | string |  | nullable | Video URL in 1080p resolution, if available |
| `mp4_720` | string |  | nullable | Video URL in 720 resolution, if available |
| `mp4_480` | string |  | nullable | Video URL in 480 resolution, if available |
| `mp4_360` | string |  | nullable | Video URL in 360 resolution, if available |
| `mp4_240` | string |  | nullable | Video URL in 240 resolution, if available |
| `mp4_144` | string |  | nullable | Video URL in 144 resolution, if available |
| `hls` | string |  | nullable | Live streaming URL, if available |

### VideoAttachmentDetails

Detailed information about video attachment including direct URLs

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `token` | string | ✓ |  | Video attachment token |
| `urls` | [VideoUrls](#videourls) |  | nullable | URLs to download or play video. Can be null if video is unavailable |
| `thumbnail` | [PhotoAttachmentPayload](#photoattachmentpayload) |  | nullable | Video thumbnail |
| `width` | integer | ✓ |  | Video width |
| `height` | integer | ✓ |  | Video height |
| `duration` | integer | ✓ |  | Video duration in seconds |

### AudioAttachment

Audio attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [MediaAttachmentPayload](#mediaattachmentpayload) | ✓ |  |  |
| `transcription` | string |  | nullable | Audio transcription |

### FileAttachment

File attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [FileAttachmentPayload](#fileattachmentpayload) | ✓ |  |  |
| `filename` | string | ✓ |  | Uploaded file name |
| `size` | integer <int64> | ✓ |  | File size in bytes |

### AttachmentPayload

Base payload for message attachments containing media URL

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ |  | Media attachment URL. For video attachments use getVideoAttachmentDetails method to obtain direct links. |

### MediaAttachmentPayload

Payload for media (video/audio) attachments with reuse token

Extends: [AttachmentPayload](#attachmentpayload)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `token` | string | ✓ |  | Use `token` in case when you are trying to reuse the same attachment in other message |

### FileAttachmentPayload

Payload for file attachments with reuse token

Extends: [AttachmentPayload](#attachmentpayload)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `token` | string | ✓ |  | Use `token` in case when you are trying to reuse the same attachment in other message |

### ContactAttachment

Contact attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [ContactAttachmentPayload](#contactattachmentpayload) | ✓ |  |  |

### ContactAttachmentPayload

Payload of contact attachment containing user contact info

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `vcf_info` | string |  | nullable | User info in VCF format |
| `hash` | string |  | nullable | User info in VCF format hash |
| `max_info` | [User](#user) |  | nullable | User info |

### StickerAttachmentPayload

Payload of sticker attachment

Extends: [AttachmentPayload](#attachmentpayload)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `code` | string | ✓ |  | Sticker identifier |

### StickerAttachment

Sticker attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [StickerAttachmentPayload](#stickerattachmentpayload) | ✓ |  |  |
| `width` | integer | ✓ |  | Sticker width |
| `height` | integer | ✓ |  | Sticker height |

### ShareAttachmentPayload

Payload of ShareAttachmentRequest

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string |  | minLength=1, nullable | URL attached to message as media preview |
| `token` | string |  | nullable | Attachment token |

### ShareAttachment

Link preview attachment with media

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [ShareAttachmentPayload](#shareattachmentpayload) | ✓ |  |  |
| `title` | string |  | nullable | Link preview title |
| `description` | string |  | nullable | Link preview description |
| `image_url` | string |  | nullable | Link preview image |

### LocationAttachment

Geographic location attachment

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `latitude` | number <double> | ✓ |  |  |
| `longitude` | number <double> | ✓ |  |  |

### InlineKeyboardAttachment

Buttons in messages

Extends: [Attachment](#attachment)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [Keyboard](#keyboard) | ✓ |  |  |

### Keyboard

Keyboard is two-dimension array of buttons

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `buttons` | [Button](#button)[][] | ✓ |  |  |

### Button

Inline keyboard button

Discriminator `type`:
- `callback` → [CallbackButton](#callbackbutton)
- `link` → [LinkButton](#linkbutton)
- `request_geo_location` → [RequestGeoLocationButton](#requestgeolocationbutton)
- `request_contact` → [RequestContactButton](#requestcontactbutton)
- `message` → [MessageButton](#messagebutton)
- `open_app` → [OpenAppButton](#openappbutton)
- `clipboard` → [ClipboardButton](#clipboardbutton)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | string | ✓ |  |  |
| `text` | string | ✓ | minLength=1, maxLength=128 | Visible text of button |

### CallbackButton

After pressing this type of button client sends to server payload it contains

Extends: [Button](#button)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | string | ✓ | maxLength=1024 | Button payload |

### LinkButton

After pressing this type of button user follows the link it contains

Extends: [Button](#button)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ | maxLength=2048 |  |

### MessageButton

After pressing this type of button it sends message from user in chat

Extends: [Button](#button)

### RequestContactButton

After pressing this type of button client sends new message with attachment of current user contact

Extends: [Button](#button)

### RequestGeoLocationButton

After pressing this type of button client sends new message with attachment of current user geo location

Extends: [Button](#button)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `quick` | boolean |  | default=False | If *true*, sends location without asking user's confirmation |

### OpenAppButton

After pressing this type of button client opens mini app

Extends: [Button](#button)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | string |  | maxLength=512, pattern='^[\\w-]*$', nullable | Button payload |
| `web_app` | string | ✓ |  | Unique public name of the bot wired to the mini app |
| `contact_id` | [UserId](#userid) |  | nullable | Unique identifier of the bot wired to the mini app |

### ClipboardButton

After pressing this type of button client copies payload data to clipboard

Extends: [Button](#button)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | string | ✓ | maxLength=1024 | Button payload |

### MessageLinkType

Type of linked message

Values: `forward`, `reply`

### AttachmentRequest

Request to attach some data to message

Discriminator `type`:
- `image` → [PhotoAttachmentRequest](#photoattachmentrequest)
- `video` → [VideoAttachmentRequest](#videoattachmentrequest)
- `audio` → [AudioAttachmentRequest](#audioattachmentrequest)
- `file` → [FileAttachmentRequest](#fileattachmentrequest)
- `sticker` → [StickerAttachmentRequest](#stickerattachmentrequest)
- `contact` → [ContactAttachmentRequest](#contactattachmentrequest)
- `inline_keyboard` → [InlineKeyboardAttachmentRequest](#inlinekeyboardattachmentrequest)
- `location` → [LocationAttachmentRequest](#locationattachmentrequest)
- `share` → [ShareAttachmentRequest](#shareattachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | string | ✓ |  |  |

### PhotoAttachmentRequest

Request to attach image to message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [PhotoAttachmentRequestPayload](#photoattachmentrequestpayload) | ✓ |  |  |

### PhotoAttachmentRequestPayload

Request to attach image. All fields are mutually exclusive

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string |  | minLength=1, nullable | Any external image URL you want to attach |
| `token` | string |  | nullable | Token of any existing attachment |
| `photos` | object |  | nullable | Tokens were obtained after uploading images |

### PhotoToken

Token representing an uploaded image

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `token` | string | ✓ |  | Encoded information of uploaded image |

### VideoAttachmentRequest

Request to attach video to message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [UploadedInfo](#uploadedinfo) | ✓ |  |  |

### AudioAttachmentRequest

Request to attach audio to message. MUST be the only attachment in message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [UploadedInfo](#uploadedinfo) | ✓ |  |  |

### UploadedInfo

This is information you will receive as soon as audio/video is uploaded

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `token` | string |  |  | Token is unique uploaded media identifier |

### FileAttachmentRequest

Request to attach file to message. MUST be the only attachment in message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [UploadedInfo](#uploadedinfo) | ✓ |  |  |

### UploadType

Type of file uploading

Values: `image`, `video`, `audio`, `file`

### ContactAttachmentRequest

Request to attach contact card to message. MUST be the only attachment in message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [ContactAttachmentRequestPayload](#contactattachmentrequestpayload) | ✓ |  |  |

### ContactAttachmentRequestPayload

Payload for contact attachment request

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `name` | string |  | nullable | Contact name |
| `contact_id` | [UserId](#userid) |  | nullable | Contact identifier if it is registered Max user |
| `vcf_info` | string |  | nullable | Full information about contact in VCF format |
| `vcf_phone` | string |  | nullable | Contact phone in VCF format |

### StickerAttachmentRequest

Request to attach sticker. MUST be the only attachment request in message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [StickerAttachmentRequestPayload](#stickerattachmentrequestpayload) | ✓ |  |  |

### StickerAttachmentRequestPayload

Payload for sticker attachment request

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `code` | string | ✓ |  | Sticker code |

### InlineKeyboardAttachmentRequest

Request to attach keyboard to message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [InlineKeyboardAttachmentRequestPayload](#inlinekeyboardattachmentrequestpayload) | ✓ |  |  |

### InlineKeyboardAttachmentRequestPayload

Payload for inline keyboard attachment request

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `buttons` | [Button](#button)[][] | ✓ | minItems=1 | Two-dimensional array of buttons |

### LocationAttachmentRequest

Request to attach geographic location to message

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `latitude` | number <double> | ✓ |  |  |
| `longitude` | number <double> | ✓ |  |  |

### ShareAttachmentRequest

Request to attach media preview of any external URL

Extends: [AttachmentRequest](#attachmentrequest)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `payload` | [ShareAttachmentPayload](#shareattachmentpayload) | ✓ |  |  |

### MarkupElement

Base type for text markup (formatting) elements

Discriminator `type`:
- `strong` → [StrongMarkup](#strongmarkup)
- `emphasized` → [EmphasizedMarkup](#emphasizedmarkup)
- `monospaced` → [MonospacedMarkup](#monospacedmarkup)
- `link` → [LinkMarkup](#linkmarkup)
- `strikethrough` → [StrikethroughMarkup](#strikethroughmarkup)
- `underline` → [UnderlineMarkup](#underlinemarkup)
- `user_mention` → [UserMentionMarkup](#usermentionmarkup)
- `heading` → [HeadingMarkup](#headingmarkup)
- `highlighted` → [HighlightedMarkup](#highlightedmarkup)
- `quote` → [QuoteMarkup](#quotemarkup)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `type` | string | ✓ |  | Type of the markup element. Can be **strong**, *emphasized*, ~strikethrough~, ++underline++, `monospaced`, highlighted, link, quote, header or user_mention |
| `from` | integer <int32> | ✓ |  | Element start index (zero-based) in text |
| `length` | integer <int32> | ✓ |  | Length of the markup element |

### StrongMarkup

Represents **bold** in text

Extends: [MarkupElement](#markupelement)

### EmphasizedMarkup

Represents *italic* in text

Extends: [MarkupElement](#markupelement)

### MonospacedMarkup

Represents `monospaced` or ```code``` block in text

Extends: [MarkupElement](#markupelement)

### LinkMarkup

Represents link in text

Extends: [MarkupElement](#markupelement)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ | minLength=1, maxLength=2048 | Link's URL |

### StrikethroughMarkup

Represents ~strikethrough~ block in text

Extends: [MarkupElement](#markupelement)

### UnderlineMarkup

Represents ++underlined++ part of the text

Extends: [MarkupElement](#markupelement)

### HeadingMarkup

Represents header part of the text

Extends: [MarkupElement](#markupelement)

### UserMentionMarkup

Represents user mention in text. Mention can be both by user's username or ID if user doesn't have username

Extends: [MarkupElement](#markupelement)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `user_link` | string |  | nullable | `@username` of mentioned user |
| `user_id` | [UserId](#userid) |  | nullable | Identifier of mentioned user without username |

### HighlightedMarkup

Represents a highlighted piece of text

Extends: [MarkupElement](#markupelement)

### QuoteMarkup

Represents quote block in text

Extends: [MarkupElement](#markupelement)

### SubscriptionRequestBody

Request to set up WebHook subscription

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | [SubscriptionUrl](#subscriptionurl) | ✓ |  |  |
| `secret` | string |  | minLength=5, maxLength=256, pattern='^[\\w-]+$' | A secret to be sent in a header “X-Max-Bot-Api-Secret” in every webhook request, 5-256 characters. Only characters A-Z, a-z, 0-9, _ and - are allowed. The header is useful to ensure that the request comes from a webhook set by you. |
| `update_types` | string[] |  |  | List of update types your bot want to receive. See `Update` object for a complete list of types |

### GetSubscriptionsResult

List of all WebHook subscriptions

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `subscriptions` | [Subscription](#subscription)[] | ✓ |  | Current subscriptions |

### SimpleQueryResult

Simple response to request

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `success` | boolean | ✓ |  | `true` if request was successful. `false` otherwise |
| `message` | string |  |  | Explanatory message if the result is not successful |

### PinMessageBody

Request body for pinning a message in chat

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message_id` | [MessageId](#messageid) | ✓ |  | Identifier of message to be pinned in chat |
| `notify` | boolean |  | default=True, nullable | If `true`, participants will be notified with system message in chat/channel |

### GetPinnedMessageResult

Result of getting pinned message in chat

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) |  | nullable | Pinned message. Can be `null` if no message pinned in chat |

### Callback

Object sent to bot when user presses button

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `timestamp` | integer <int64> | ✓ |  | Unix-time when user pressed the button |
| `callback_id` | string | ✓ |  | Current keyboard identifier |
| `payload` | string |  |  | Button payload |
| `user` | [User](#user) | ✓ |  | User pressed the button |

### CallbackAnswer

Send this object when your bot wants to react to when a button is pressed

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [NewMessageBody](#newmessagebody) |  | nullable | Fill this if you want to modify current message |
| `notification` | string |  | nullable | Fill this if you just want to send one-time notification to user |

### Error

Server returns this if there was an exception to your request

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `error` | string |  |  | Error |
| `code` | string | ✓ |  | Error code |
| `message` | string | ✓ |  | Human-readable description |

### UploadEndpoint

Endpoint you should upload to your binaries

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `url` | string | ✓ |  | URL to upload |
| `token` | string |  | nullable | Video or audio token for send message |

### UserIdsList

List of user identifiers

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `user_ids` | object | ✓ | maxItems=100 |  |

### ActionRequestBody

Request body for sending action to chat

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `action` | [SenderAction](#senderaction) | ✓ |  |  |

### ChatAdminsList

List of chat administrators with permissions

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `admins` | [ChatAdmin](#chatadmin)[] | ✓ |  |  |

### ChatAdmin

Administrator id with permissions

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `user_id` | [UserId](#userid) | ✓ |  |  |
| `permissions` | [ChatAdminPermission](#chatadminpermission)[] | ✓ |  |  |
| `alias` | string |  | nullable | Alias of the admin in chat. By default, `null` |

### SenderAction

Different actions to send to chat members

Values: `typing_on`, `sending_photo`, `sending_video`, `sending_audio`, `sending_file`, `mark_seen`

### UpdateList

List of all updates in chats your bot participated in

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `updates` | [Update](#update)[] | ✓ |  | Page of updates |
| `marker` | integer <int64> |  | nullable | Pointer to the next data page |

### Update

`Update` object represents different types of events that happened in chat. See its inheritors

Discriminator `update_type`:
- `message_created` → [MessageCreatedUpdate](#messagecreatedupdate)
- `message_callback` → [MessageCallbackUpdate](#messagecallbackupdate)
- `message_edited` → [MessageEditedUpdate](#messageeditedupdate)
- `message_removed` → [MessageRemovedUpdate](#messageremovedupdate)
- `comment_created` → [CommentCreatedUpdate](#commentcreatedupdate)
- `comment_edited` → [CommentEditedUpdate](#commenteditedupdate)
- `comment_removed` → [CommentRemovedUpdate](#commentremovedupdate)
- `bot_added` → [BotAddedToChatUpdate](#botaddedtochatupdate)
- `bot_removed` → [BotRemovedFromChatUpdate](#botremovedfromchatupdate)
- `user_added` → [UserAddedToChatUpdate](#useraddedtochatupdate)
- `user_removed` → [UserRemovedFromChatUpdate](#userremovedfromchatupdate)
- `bot_started` → [BotStartedUpdate](#botstartedupdate)
- `bot_stopped` → [BotStoppedUpdate](#botstoppedupdate)
- `dialog_cleared` → [DialogClearedUpdate](#dialogclearedupdate)
- `dialog_removed` → [DialogRemovedUpdate](#dialogremovedupdate)
- `dialog_muted` → [DialogMutedUpdate](#dialogmutedupdate)
- `dialog_unmuted` → [DialogUnmutedUpdate](#dialogunmutedupdate)
- `chat_title_changed` → [ChatTitleChangedUpdate](#chattitlechangedupdate)
- `bot_admin_permissions_changed` → [BotAdminPermissionsChangedUpdate](#botadminpermissionschangedupdate)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `update_type` | string | ✓ |  |  |
| `timestamp` | integer <int64> | ✓ |  | Unix-time when event has occurred |

### MessageCallbackUpdate

You will get this `update` as soon as user presses button

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `callback` | [Callback](#callback) | ✓ |  |  |
| `message` | [Message](#message) |  | nullable | Original message containing inline keyboard. Can be `null` in case it had been deleted by the moment a bot got this update |
| `user_locale` | string |  | nullable | Current user locale in IETF BCP 47 format |

### MessageCreatedUpdate

You will get this `update` as soon as message is created. In group chats bot receives this update only if it is administrator with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) | ✓ |  | Newly created message |
| `user_locale` | string |  | nullable | Current user locale in IETF BCP 47 format. Available only in dialogs |

### MessageRemovedUpdate

You will get this `update` as soon as message is removed. In group chats bot receives this update only if it is administrator with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message_id` | [MessageId](#messageid) | ✓ |  | Identifier of removed message |
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where message has been deleted |
| `user_id` | [UserId](#userid) | ✓ |  | User who deleted this message |

### MessageEditedUpdate

You will get this `update` as soon as message is edited. In group chats bot receives this update only if it is administrator with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) | ✓ |  | Edited message |

### CommentCreatedUpdate

You will get this `update` as soon as comment is created. Bot receives this update only if it is administrator of the channel with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) | ✓ |  | Newly created comment |

### CommentRemovedUpdate

You will get this `update` as soon as comment is removed. Bot receives this update only if it is administrator of the channel with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message_id` | [MessageId](#messageid) | ✓ |  | Identifier of removed comment |
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where comment has been deleted |
| `user_id` | [UserId](#userid) | ✓ |  | User who deleted this comment |
| `post_id` | [MessageId](#messageid) | ✓ |  | Post identifier |

### CommentEditedUpdate

You will get this `update` as soon as comment is edited. Bot receives this update only if it is administrator of the channel with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `message` | [Message](#message) | ✓ |  | Edited comment |

### BotAddedToChatUpdate

You will receive this update when bot has been added to chat

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat id where bot was added |
| `user` | [User](#user) | ✓ |  | User who added bot to chat |
| `is_channel` | boolean | ✓ |  | Indicates whether bot has been added to channel or not |

### BotRemovedFromChatUpdate

You will receive this update when bot has been removed from chat

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier bot removed from |
| `user` | [User](#user) | ✓ |  | User who removed bot from chat |
| `is_channel` | boolean | ✓ |  | Indicates whether bot has been removed from channel or not |

### UserAddedToChatUpdate

You will receive this update when user has been added to chat where bot is administrator with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User added to chat |
| `inviter_id` | [UserId](#userid) |  | nullable | User who added user to chat. Can be `null` in case when user joined chat by link |
| `is_channel` | boolean | ✓ |  | Indicates whether user has been added to channel or not |

### UserRemovedFromChatUpdate

You will receive this update when user has been removed from chat where bot is administrator with `read_all_messages` permission

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User removed from chat |
| `admin_id` | [UserId](#userid) |  |  | Administrator who removed user from chat. Can be `null` in case when user left chat |
| `is_channel` | boolean | ✓ |  | Indicates whether user has been removed from channel or not |

### BotStartedUpdate

Bot gets this type of update as soon as user pressed `Start` button

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User pressed the 'Start' button |
| `payload` | string |  | maxLength=512, nullable | Additional data from deep-link passed on bot startup |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### BotStoppedUpdate

Bot gets this type of update as soon as bot has been stopped

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who stopped the bot |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### DialogClearedUpdate

Bot gets this type of update as soon as dialog history has been cleared

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who cleared the dialog |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### DialogRemovedUpdate

Bot gets this type of update as soon as dialog has been removed

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who removed the dialog |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### DialogMutedUpdate

Bot gets this type of update as soon as dialog has been muted

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who muted the dialog |
| `muted_until` | integer <int64> | ✓ |  | Unix-time until which the dialog was muted |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### DialogUnmutedUpdate

Bot gets this type of update as soon as dialog has been unmuted

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Dialog identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who unmuted the dialog |
| `user_locale` | string |  |  | Current user locale in IETF BCP 47 format |

### ChatTitleChangedUpdate

Bot gets this type of update as soon as title has been changed in chat

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where event has occurred |
| `user` | [User](#user) | ✓ |  | User who changed title |
| `title` | string | ✓ |  | New title |

### BotAdminPermissionsChangedUpdate

Bot will get this update when bot admin permissions changed

Extends: [Update](#update)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `chat_id` | [ChatId](#chatid) | ✓ |  | Chat identifier where event has occurred |
| `user_id` | [UserId](#userid) | ✓ |  | User or bot who changed bot admin permissions |
| `bot_id` | [UserId](#userid) | ✓ |  | Bot that admin permissions changed |
| `is_channel` | boolean | ✓ |  | Indicates whether bot admin permissions has been changed in channel or not |
| `is_admin` | boolean | ✓ |  | Indicates whether bot is admin in chat/channel or not |
| `permissions` | [ChatAdminPermission](#chatadminpermission)[] |  | nullable |  |

### ModifyMembersResult

Result of members list modification request

Extends: [SimpleQueryResult](#simplequeryresult)

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `failed_user_ids` | [UserId](#userid)[] |  | nullable | List of user IDs failed to add or delete |
| `failed_user_details` | [FailedUserDetails](#faileduserdetails)[] |  | nullable |  |

### FailedUserDetails

Detailed info about why a user cannot be added to the chat.

| Field | Type | Req | Constraints | Description |
|---|---|---|---|---|
| `error_code` | string | ✓ |  | Code add.participant.privacy - Privacy errors while add participants. Code add.participant.not.found - Users to add not found |
| `user_ids` | [UserId](#userid)[] | ✓ |  | List of user IDs failed to add |
