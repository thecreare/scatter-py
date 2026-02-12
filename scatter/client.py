"""Main client class for scatter.py."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from .events import EVENT_MAP, parse_event
from .gateway import Gateway
from .http import HTTPClient
from .models import (
    Channel,
    ChannelCategory,
    CustomEmoji,
    Invite,
    Member,
    Message,
    Role,
    Space,
)

log = logging.getLogger(__name__)

# How often to re-send the typing indicator (seconds).
# Scatter typing indicators expire after ~5s on the client side.
_TYPING_INTERVAL = 4.0


class Typing:
    """Async context manager that sends typing indicators continuously.

    Usage::

        async with client.typing(channel_id):
            # bot appears to be typing while this block executes
            result = await some_slow_operation()
            await client.send_message(space_id, channel_id, result)
    """

    def __init__(self, client: Client, channel_id: str):
        self._client = client
        self._channel_id = channel_id
        self._task: asyncio.Task | None = None

    async def __aenter__(self):
        await self._client.send_typing(self._channel_id)
        self._task = asyncio.create_task(self._loop())
        return self

    async def __aexit__(self, *exc):
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        try:
            while True:
                await asyncio.sleep(_TYPING_INTERVAL)
                await self._client.send_typing(self._channel_id)
        except asyncio.CancelledError:
            pass


class Client:
    """The main interface for a Scatter bot.

    Example usage::

        import scatter

        client = scatter.Client("scatter_bot_...")

        @client.event
        async def on_ready(data):
            print("Bot is ready!")

        @client.event
        async def on_message(message):
            if message.content == "!ping":
                await client.send_message(
                    message.space_id, message.channel_id, "Pong!"
                )

        client.run()
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str | None = None,
        ws_url: str | None = None,
    ):
        self._token = token
        self.user_id: str | None = None

        http_kwargs: dict[str, Any] = {}
        gw_kwargs: dict[str, Any] = {}
        if base_url:
            http_kwargs["base_url"] = base_url
        if ws_url:
            gw_kwargs["ws_url"] = ws_url

        self.http = HTTPClient(token, **http_kwargs)
        self._gateway = Gateway(token, self._dispatch, **gw_kwargs)
        self._event_handlers: dict[str, Callable[..., Coroutine]] = {}
        self._listeners: dict[str, list[Callable[..., Coroutine]]] = {}

    # ── Event Registration ──────────────────────────────────────

    def event(self, coro: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        """Decorator to register an event handler by function name.

        The function name must start with ``on_``.

        Example::

            @client.event
            async def on_message(message):
                ...
        """
        name = coro.__name__
        if not name.startswith("on_"):
            raise ValueError(f"Event handler name must start with 'on_', got '{name}'")
        self._event_handlers[name] = coro
        return coro

    def listen(self, event_name: str | None = None):
        """Decorator to add an additional listener for a specific event.

        Unlike ``@client.event``, multiple listeners can be registered
        for the same event.

        Example::

            @client.listen("on_message")
            async def log_messages(message):
                print(message.content)
        """

        def decorator(coro: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
            key = event_name or coro.__name__
            self._listeners.setdefault(key, []).append(coro)
            return coro

        return decorator

    # ── Internal Dispatch ───────────────────────────────────────

    async def _dispatch(self, event_type: str, data: dict):
        """Called by the Gateway for each incoming WS event."""
        # Map raw event type to handler name
        mapped = EVENT_MAP.get(event_type)
        if mapped is None:
            log.debug("Unhandled event type: %s", event_type)
            return

        handler_name = f"on_{mapped}"

        # Special handling for ready event
        if mapped == "ready":
            self.user_id = data.get("user_id")

        # Parse the raw data into model objects
        parsed = parse_event(event_type, data)

        # Call the @client.event handler
        handler = self._event_handlers.get(handler_name)
        if handler is not None:
            try:
                await handler(parsed)
            except Exception:
                log.exception("Error in event handler %s", handler_name)

        # Call all @client.listen handlers
        for listener in self._listeners.get(handler_name, []):
            try:
                await listener(parsed)
            except Exception:
                log.exception("Error in listener for %s", handler_name)

    # ── Connection ──────────────────────────────────────────────

    async def start(self):
        """Connect to the gateway and block until disconnected."""
        await self._gateway.connect()

    async def close(self):
        """Gracefully close the gateway and HTTP connections."""
        await self._gateway.close()
        await self.http.close()

    def run(self):
        """Blocking convenience method that starts the event loop.

        Equivalent to ``asyncio.run(client.start())``.
        """
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            pass

    # ── Subscriptions ───────────────────────────────────────────

    async def subscribe_channel(self, channel_id: str):
        """Subscribe to events for a channel (messages, typing, reactions)."""
        self._gateway.track_channel(channel_id)
        await self._gateway.send(
            {"type": "subscribe", "channel_id": channel_id}
        )

    async def unsubscribe_channel(self, channel_id: str):
        """Unsubscribe from channel events."""
        self._gateway.untrack_channel(channel_id)
        await self._gateway.send(
            {"type": "unsubscribe", "channel_id": channel_id}
        )

    async def subscribe_space(self, space_id: str):
        """Subscribe to space events (members, roles, channels, etc.)."""
        self._gateway.track_space(space_id)
        await self._gateway.send(
            {"type": "subscribe_space", "space_id": space_id}
        )

    async def unsubscribe_space(self, space_id: str):
        """Unsubscribe from space events."""
        self._gateway.untrack_space(space_id)
        await self._gateway.send(
            {"type": "unsubscribe_space", "space_id": space_id}
        )

    async def send_typing(self, channel_id: str):
        """Send a single typing indicator for a channel."""
        await self._gateway.send(
            {"type": "typing", "channel_id": channel_id}
        )

    def typing(self, channel_id: str) -> Typing:
        """Return an async context manager that sends typing indicators.

        Usage::

            async with client.typing(channel_id):
                result = await some_slow_operation()
                await client.send_message(space_id, channel_id, result)
        """
        return Typing(self, channel_id)

    # ── REST Convenience Methods ────────────────────────────────

    async def fetch_spaces(self) -> list[Space]:
        """Fetch all spaces the bot is a member of."""
        data = await self.http.get_spaces()
        return [Space.from_dict(s) for s in data]

    async def fetch_space(self, space_id: str) -> Space:
        """Fetch a single space by ID.

        Sub-resources (channels, members, roles, categories, emojis) are
        not included. Use :meth:`fetch_channels`, :meth:`fetch_members`,
        etc. to load them on demand.
        """
        data = await self.http.get_space(space_id)
        return Space.from_dict(data)

    async def fetch_channels(self, space_id: str) -> list[Channel]:
        """Fetch all channels in a space."""
        data = await self.http.get_channels(space_id)
        return [Channel.from_dict(c) for c in data]

    async def fetch_members(self, space_id: str) -> list[Member]:
        """Fetch all members in a space."""
        data = await self.http.get_members(space_id)
        return [Member.from_dict(m) for m in data]

    async def fetch_roles(self, space_id: str) -> list[Role]:
        """Fetch all roles in a space."""
        data = await self.http.get_roles(space_id)
        return [Role.from_dict(r) for r in data]

    async def fetch_categories(self, space_id: str) -> list[ChannelCategory]:
        """Fetch all channel categories in a space."""
        data = await self.http.get_categories(space_id)
        return [ChannelCategory.from_dict(c) for c in data]

    async def fetch_messages(
        self,
        space_id: str,
        channel_id: str,
        *,
        before: str | None = None,
        limit: int | None = None,
    ) -> list[Message]:
        """Fetch messages from a channel."""
        data = await self.http.get_messages(
            space_id, channel_id, before=before, limit=limit
        )
        return [Message.from_dict(m, space_id=space_id) for m in data]

    async def send_message(
        self,
        space_id: str,
        channel_id: str,
        content: str,
        *,
        reply_to: str | None = None,
    ) -> Message:
        """Send a message to a channel."""
        data = await self.http.send_message(
            space_id, channel_id, content, reply_to=reply_to
        )
        return Message.from_dict(data, space_id=space_id)

    async def edit_message(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> Message:
        """Edit a message."""
        data = await self.http.edit_message(
            space_id, channel_id, message_id, content
        )
        return Message.from_dict(data, space_id=space_id)

    async def delete_message(
        self, space_id: str, channel_id: str, message_id: str
    ) -> None:
        """Delete a message."""
        await self.http.delete_message(space_id, channel_id, message_id)

    async def add_reaction(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message."""
        await self.http.add_reaction(space_id, channel_id, message_id, emoji)

    async def remove_reaction(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message."""
        await self.http.remove_reaction(
            space_id, channel_id, message_id, emoji
        )

    async def fetch_emojis(self, space_id: str) -> list[CustomEmoji]:
        """Fetch custom emojis in a space."""
        data = await self.http.get_emojis(space_id)
        return [CustomEmoji.from_dict(e) for e in data]

    async def fetch_invites(self, space_id: str) -> list[Invite]:
        """Fetch invites for a space."""
        data = await self.http.get_invites(space_id)
        return [Invite.from_dict(i) for i in data]

    async def create_invite(
        self,
        space_id: str,
        *,
        max_uses: int | None = None,
        expires_in_seconds: int | None = None,
    ) -> Invite:
        """Create an invite for a space."""
        data = await self.http.create_invite(
            space_id,
            max_uses=max_uses,
            expires_in_seconds=expires_in_seconds,
        )
        return Invite.from_dict(data)
