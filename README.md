# scatter.py

Python library for building bots on the [Scatter](https://scatter.starforge.games) chat platform.

Requires Python 3.11+ and [aiohttp](https://docs.aiohttp.org/).

## Install

```bash
pip install scatter.py
```

Or from source:

```bash
git clone https://github.com/kyle-emmerich/scatter-py.git
cd scatter-py
pip install -e .
```

## Quick Start

```python
import os
import scatter

client = scatter.Client(os.environ["SCATTER_TOKEN"])

@client.event
async def on_ready(data):
    print(f"Logged in as {client.user_id}")

    # Subscribe to everything so we receive events
    spaces = await client.fetch_spaces()
    for space in spaces:
        await client.subscribe_space(space.id)
        channels = await client.fetch_channels(space.id)
        for ch in channels:
            await client.subscribe_channel(ch.id)

@client.event
async def on_message(message: scatter.Message):
    if message.author.id == client.user_id:
        return
    if message.content == "!ping":
        await client.send_message(message.space_id, message.channel_id, "Pong!")

client.run()
```

See [`examples/ping_bot.py`](examples/ping_bot.py) for a more complete example.

## Getting a Bot Token

1. In Scatter, go to **User Settings > Developer** and enable Developer Mode
2. Create an OAuth App, add a Bot to it, and generate a token
3. The token starts with `scatter_bot_`. Set it as `SCATTER_TOKEN` or pass it directly to the client

## How It Works

### Client & Events

The `Client` handles the WebSocket connection and calls your event handlers when things happen.

```python
client = scatter.Client("scatter_bot_...")
```

Register handlers with `@client.event`. The function name determines the event: `on_message` for new messages, `on_member_join` when someone joins a space, etc.

```python
@client.event
async def on_message(message: scatter.Message):
    ...

@client.event
async def on_member_join(user: scatter.User):
    print(f"{user.display_name} joined!")
```

If you need multiple handlers for the same event, use `@client.listen`:

```python
@client.listen("on_message")
async def log_all(message):
    print(f"{message.author.username}: {message.content}")

@client.listen("on_message")
async def react_to_greetings(message):
    if "hello" in message.content.lower():
        await client.add_reaction(message.space_id, message.channel_id, message.id, "👋")
```

### Subscriptions

You won't receive events unless you subscribe to the relevant spaces/channels:

```python
await client.subscribe_space(space.id)       # member joins, role changes, etc.
await client.subscribe_channel(channel.id)   # messages, typing, reactions, etc.
```

These are automatically restored if the WebSocket reconnects.

### Typing Indicators

```python
async with client.typing(channel_id):
    result = await slow_computation()
    await client.send_message(space_id, channel_id, result)
```

Sends a typing indicator immediately and re-sends every 4 seconds until the block exits.

## REST Methods

Every method takes `space_id` explicitly since Scatter's API is scoped to spaces.

### Messages

```python
msg = await client.send_message(space_id, channel_id, "Hello!")
msg = await client.send_message(space_id, channel_id, "Reply!", reply_to=message_id)
msg = await client.edit_message(space_id, channel_id, message_id, "Edited")
await client.delete_message(space_id, channel_id, message_id)
messages = await client.fetch_messages(space_id, channel_id, limit=50, before=message_id)
```

### Reactions

```python
await client.add_reaction(space_id, channel_id, message_id, "👍")
await client.remove_reaction(space_id, channel_id, message_id, "👍")
```

### Spaces, Channels, Members

```python
spaces = await client.fetch_spaces()
space = await client.fetch_space(space_id)
channels = await client.fetch_channels(space_id)
members = await client.fetch_members(space_id)
roles = await client.fetch_roles(space_id)
categories = await client.fetch_categories(space_id)
emojis = await client.fetch_emojis(space_id)
```

### Invites

```python
invite = await client.create_invite(space_id, max_uses=10, expires_in_seconds=86400)
invites = await client.fetch_invites(space_id)
```

### Low-Level HTTP Client

For operations not wrapped by convenience methods (channel management, role CRUD, pins, kicks, file uploads), use `client.http` directly:

```python
await client.http.create_channel(space_id, "bot-logs", topic="Automated logs")
await client.http.delete_channel(space_id, channel_id)
await client.http.create_role(space_id, "Moderator", color=0x3498db, hoist=True)
await client.http.update_role(space_id, role_id, name="Senior Mod")
await client.http.delete_role(space_id, role_id)
await client.http.set_member_roles(space_id, user_id, [role_id_1, role_id_2])
await client.http.kick_member(space_id, user_id)
await client.http.pin_message(space_id, channel_id, message_id)
await client.http.unpin_message(space_id, channel_id, message_id)
await client.http.upload_file(space_id, channel_id, "/path/to/image.png")
```

## Events Reference

| WebSocket Type | Handler | Parsed As |
|---|---|---|
| `auth_ok` | `on_ready` | `dict` |
| `new_message` | `on_message` | `Message` |
| `message_edited` | `on_message_edit` | `dict` |
| `message_deleted` | `on_message_delete` | `dict` |
| `typing` | `on_typing` | `dict` |
| `reaction_added` | `on_reaction_add` | `dict` |
| `reaction_removed` | `on_reaction_remove` | `dict` |
| `message_pinned` | `on_message_pinned` | `dict` |
| `message_unpinned` | `on_message_unpinned` | `dict` |
| `member_joined` | `on_member_join` | `User` |
| `member_left` | `on_member_remove` | `dict` |
| `presence_changed` | `on_presence_update` | `dict` |
| `member_profile_updated` | `on_member_update` | `dict` |
| `member_roles_updated` | `on_member_roles_update` | `dict` |
| `channel_created` | `on_channel_create` | `Channel` |
| `channel_updated` | `on_channel_update` | `Channel` |
| `channel_deleted` | `on_channel_delete` | `dict` |
| `role_created` | `on_role_create` | `Role` |
| `role_updated` | `on_role_update` | `Role` |
| `role_deleted` | `on_role_delete` | `dict` |
| `emoji_created` | `on_emoji_create` | `dict` |
| `emoji_deleted` | `on_emoji_delete` | `dict` |
| `category_created` | `on_category_create` | `ChannelCategory` |
| `category_updated` | `on_category_update` | `ChannelCategory` |
| `category_deleted` | `on_category_delete` | `dict` |
| `mention` | `on_mention` | `dict` |
| `dm_new_message` | `on_dm_message` | `Message` |
| `dm_message_edited` | `on_dm_message_edit` | `dict` |
| `dm_message_deleted` | `on_dm_message_delete` | `dict` |
| `dm_typing` | `on_dm_typing` | `dict` |
| `voice_participant_joined` | `on_voice_join` | `dict` |
| `voice_participant_left` | `on_voice_leave` | `dict` |

Events listed as `dict` give you the raw WebSocket payload. The rest are parsed into model objects.

## Models

All models are dataclasses with `from_dict()` class methods:

- **`Message`**: `id`, `channel_id`, `content`, `author` (User), `space_id`, `embeds`, `attachments`, `reactions`, `created_at`, `edited_at`, `reply_to`
- **`User`**: `id`, `username`, `display_name`, `avatar_url`, `presence`, `subscription_tier`
- **`Member`**: same as User plus `roles` (list of MemberRoleInfo) and `joined_at`
- **`Space`**: `id`, `name`, `description`, `icon_url`, `owner_id`, `is_public`. Optional lazy-loaded fields (default `None`): `channels`, `members`, `roles`, `categories`, `custom_emojis` — use `fetch_channels()`, `fetch_members()`, etc. to load these
- **`Channel`**: `id`, `space_id`, `name`, `channel_type`, `topic`, `position`, `category_id`
- **`Role`**: `id`, `space_id`, `name`, `color`, `position`, `permissions`, `hoist`, `is_default`, `inherits_from`
- **`Attachment`**: `id`, `filename`, `content_type`, `size_bytes`, `url`, `width`, `height`
- **`Embed`**: `id`, `url`, `embed_type`, `title`, `description`, `thumbnail_url`, `video_url`
- **`Reaction`**: `emoji`, `count`, `user_reacted`
- **`CustomEmoji`**: `id`, `space_id`, `name`, `image_url`
- **`Invite`**: `id`, `space_id`, `code`, `max_uses`, `use_count`, `url`, `expires_at`

## Enums

```python
from scatter import Permission, ChannelType, PresenceStatus

Permission.SEND_MESSAGES      # "send_messages"
Permission.MANAGE_CHANNELS    # "manage_channels"
Permission.MANAGE_ROLES       # "manage_roles"
Permission.KICK_MEMBERS       # "kick_members"
Permission.MANAGE_SPACE       # "manage_space"
Permission.MANAGE_MESSAGES    # "manage_messages"
Permission.ATTACH_FILES       # "attach_files"
Permission.EMBED_LINKS        # "embed_links"
Permission.MENTION_EVERYONE   # "mention_everyone"
Permission.PIN_MESSAGES       # "pin_messages"
Permission.CREATE_INVITES     # "create_invites"
Permission.MANAGE_INVITES     # "manage_invites"

ChannelType.TEXT              # "text"
ChannelType.VOICE             # "voice"

PresenceStatus.ONLINE         # "online"
PresenceStatus.IDLE           # "idle"
PresenceStatus.DND            # "dnd"
PresenceStatus.OFFLINE        # "offline"
```

## Error Handling

```python
try:
    await client.send_message(space_id, channel_id, "Hello!")
except scatter.Forbidden as e:
    print(f"No permission: {e}")
except scatter.NotFound:
    print("Channel or space not found")
except scatter.HTTPException as e:
    print(f"API error {e.status}: {e}")
except scatter.AuthenticationError:
    print("Invalid bot token")
```

```
ScatterException
├── HTTPException
│   ├── NotFound        (404)
│   └── Forbidden       (403)
├── GatewayError
└── AuthenticationError
```

## Logging

Uses Python's `logging` module. To see HTTP requests and WebSocket traffic:

```python
import logging
logging.getLogger("scatter").setLevel(logging.DEBUG)
```

## Manual Lifecycle Control

`client.run()` is a blocking convenience wrapper around `asyncio.run(client.start())`. If you need to manage the event loop yourself:

```python
async def main():
    client = scatter.Client(token)

    @client.event
    async def on_ready(data):
        print("Ready!")

    try:
        await client.start()
    finally:
        await client.close()

asyncio.run(main())
```

## License

MIT
