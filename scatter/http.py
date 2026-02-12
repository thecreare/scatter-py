"""HTTP client for the Scatter REST API."""

from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp

from .errors import Forbidden, HTTPException, NotFound

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://scatter.starforge.games/api"


class HTTPClient:
    """Low-level REST API client. Methods return raw dicts/lists."""

    def __init__(self, token: str, *, base_url: str = DEFAULT_BASE_URL):
        self._token = token
        self._base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                }
            )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        await self._ensure_session()
        assert self._session is not None
        url = f"{self._base_url}{path}"
        log.debug("%s %s", method, url)

        async with self._session.request(
            method, url, json=json, params=params
        ) as resp:
            if resp.status == 204:
                return {}
            body = await resp.json(content_type=None)
            if resp.status >= 400:
                if resp.status == 404:
                    raise NotFound(resp.status, body if isinstance(body, dict) else {"error": str(body)})
                if resp.status == 403:
                    raise Forbidden(resp.status, body if isinstance(body, dict) else {"error": str(body)})
                raise HTTPException(resp.status, body if isinstance(body, dict) else {"error": str(body)})
            return body

    # ── Spaces ──────────────────────────────────────────────────

    async def get_spaces(self) -> list[dict]:
        return await self.request("GET", "/spaces/me")

    async def get_space(self, space_id: str) -> dict:
        return await self.request("GET", f"/spaces/{space_id}")

    # ── Members ─────────────────────────────────────────────────

    async def get_members(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/members")

    async def set_member_roles(
        self, space_id: str, user_id: str, role_ids: list[str]
    ) -> None:
        await self.request(
            "PUT",
            f"/spaces/{space_id}/members/{user_id}/roles",
            json={"role_ids": role_ids},
        )

    async def kick_member(self, space_id: str, user_id: str) -> None:
        await self.request(
            "DELETE", f"/spaces/{space_id}/members/{user_id}"
        )

    # ── Channels ────────────────────────────────────────────────

    async def get_channels(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/channels")

    async def create_channel(
        self,
        space_id: str,
        name: str,
        *,
        topic: str | None = None,
        category_id: str | None = None,
        channel_type: str = "text",
    ) -> dict:
        body: dict = {"name": name, "channel_type": channel_type}
        if topic is not None:
            body["topic"] = topic
        if category_id is not None:
            body["category_id"] = category_id
        return await self.request(
            "POST", f"/spaces/{space_id}/channels", json=body
        )

    async def update_channel(
        self, space_id: str, channel_id: str, **kwargs
    ) -> dict:
        return await self.request(
            "PATCH",
            f"/spaces/{space_id}/channels/{channel_id}",
            json=kwargs,
        )

    async def delete_channel(self, space_id: str, channel_id: str) -> None:
        await self.request(
            "DELETE", f"/spaces/{space_id}/channels/{channel_id}"
        )

    # ── Messages ────────────────────────────────────────────────

    async def get_messages(
        self,
        space_id: str,
        channel_id: str,
        *,
        before: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        params: dict[str, str] = {}
        if before:
            params["before"] = before
        if limit:
            params["limit"] = str(limit)
        return await self.request(
            "GET",
            f"/spaces/{space_id}/channels/{channel_id}/messages",
            params=params or None,
        )

    async def send_message(
        self,
        space_id: str,
        channel_id: str,
        content: str,
        *,
        reply_to: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> dict:
        body: dict = {"content": content}
        if reply_to:
            body["reply_to"] = reply_to
        if attachment_ids:
            body["attachment_ids"] = attachment_ids
        return await self.request(
            "POST",
            f"/spaces/{space_id}/channels/{channel_id}/messages",
            json=body,
        )

    async def edit_message(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> dict:
        return await self.request(
            "PATCH",
            f"/spaces/{space_id}/channels/{channel_id}/messages/{message_id}",
            json={"content": content},
        )

    async def delete_message(
        self, space_id: str, channel_id: str, message_id: str
    ) -> None:
        await self.request(
            "DELETE",
            f"/spaces/{space_id}/channels/{channel_id}/messages/{message_id}",
        )

    # ── Reactions ───────────────────────────────────────────────

    async def add_reaction(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict:
        return await self.request(
            "PUT",
            f"/spaces/{space_id}/channels/{channel_id}/messages"
            f"/{message_id}/reactions/{quote(emoji)}",
        )

    async def remove_reaction(
        self,
        space_id: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> dict:
        return await self.request(
            "DELETE",
            f"/spaces/{space_id}/channels/{channel_id}/messages"
            f"/{message_id}/reactions/{quote(emoji)}",
        )

    # ── Pins ────────────────────────────────────────────────────

    async def get_pins(self, space_id: str, channel_id: str) -> list[dict]:
        return await self.request(
            "GET", f"/spaces/{space_id}/channels/{channel_id}/pins"
        )

    async def pin_message(
        self, space_id: str, channel_id: str, message_id: str
    ) -> None:
        await self.request(
            "PUT",
            f"/spaces/{space_id}/channels/{channel_id}/pins/{message_id}",
        )

    async def unpin_message(
        self, space_id: str, channel_id: str, message_id: str
    ) -> None:
        await self.request(
            "DELETE",
            f"/spaces/{space_id}/channels/{channel_id}/pins/{message_id}",
        )

    # ── Roles ───────────────────────────────────────────────────

    async def get_roles(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/roles")

    async def create_role(
        self,
        space_id: str,
        name: str,
        *,
        color: int | None = None,
        hoist: bool | None = None,
    ) -> dict:
        body: dict = {"name": name}
        if color is not None:
            body["color"] = color
        if hoist is not None:
            body["hoist"] = hoist
        return await self.request(
            "POST", f"/spaces/{space_id}/roles", json=body
        )

    async def update_role(
        self, space_id: str, role_id: str, **kwargs
    ) -> dict:
        return await self.request(
            "PATCH", f"/spaces/{space_id}/roles/{role_id}", json=kwargs
        )

    async def delete_role(self, space_id: str, role_id: str) -> None:
        await self.request(
            "DELETE", f"/spaces/{space_id}/roles/{role_id}"
        )

    # ── Invites ─────────────────────────────────────────────────

    async def create_invite(
        self,
        space_id: str,
        *,
        max_uses: int | None = None,
        expires_in_seconds: int | None = None,
    ) -> dict:
        body: dict = {}
        if max_uses is not None:
            body["max_uses"] = max_uses
        if expires_in_seconds is not None:
            body["expires_in_seconds"] = expires_in_seconds
        return await self.request(
            "POST", f"/spaces/{space_id}/invites", json=body or None
        )

    async def get_invites(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/invites")

    # ── Categories ───────────────────────────────────────────────

    async def get_categories(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/categories")

    # ── Emojis ──────────────────────────────────────────────────

    async def get_emojis(self, space_id: str) -> list[dict]:
        return await self.request("GET", f"/spaces/{space_id}/emojis")

    # ── File Uploads ────────────────────────────────────────────

    async def upload_file(
        self, space_id: str, channel_id: str, file_path: str
    ) -> dict:
        """Upload a file attachment (multipart/form-data)."""
        import os

        await self._ensure_session()
        assert self._session is not None

        data = aiohttp.FormData()
        data.add_field(
            "file",
            open(file_path, "rb"),  # noqa: SIM115
            filename=os.path.basename(file_path),
        )

        url = (
            f"{self._base_url}/spaces/{space_id}"
            f"/channels/{channel_id}/attachments"
        )
        headers = {"Authorization": f"Bearer {self._token}"}

        async with self._session.post(url, data=data, headers=headers) as resp:
            body = await resp.json(content_type=None)
            if resp.status >= 400:
                raise HTTPException(resp.status, body if isinstance(body, dict) else {"error": str(body)})
            return body
