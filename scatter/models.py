"""Data models for the Scatter API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class User:
    id: str
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    presence: str = "offline"
    custom_status: Optional[str] = None
    subscription_tier: str = "free"
    is_admin: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> User:
        return cls(
            id=d["id"],
            username=d.get("username", ""),
            display_name=d.get("display_name", ""),
            avatar_url=d.get("avatar_url"),
            presence=d.get("presence", "offline"),
            custom_status=d.get("custom_status"),
            subscription_tier=d.get("subscription_tier", "free"),
            is_admin=d.get("is_admin", False),
        )


@dataclass
class MemberRoleInfo:
    id: str
    name: str
    color: Optional[int] = None
    position: int = 0
    hoist: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> MemberRoleInfo:
        return cls(
            id=d["id"],
            name=d["name"],
            color=d.get("color"),
            position=d.get("position", 0),
            hoist=d.get("hoist", False),
        )


@dataclass
class Member:
    """A user within a specific space, with role info."""

    id: str
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    presence: str = "offline"
    custom_status: Optional[str] = None
    subscription_tier: str = "free"
    roles: list[MemberRoleInfo] = field(default_factory=list)
    joined_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: dict) -> Member:
        return cls(
            id=d["id"],
            username=d.get("username", ""),
            display_name=d.get("display_name", ""),
            avatar_url=d.get("avatar_url"),
            presence=d.get("presence", "offline"),
            custom_status=d.get("custom_status"),
            subscription_tier=d.get("subscription_tier", "free"),
            roles=[MemberRoleInfo.from_dict(r) for r in d.get("roles", [])],
            joined_at=_parse_dt(d.get("joined_at")),
        )


@dataclass
class RolePermission:
    permission: str
    granted: bool

    @classmethod
    def from_dict(cls, d: dict) -> RolePermission:
        return cls(permission=d["permission"], granted=d["granted"])


@dataclass
class Role:
    id: str
    space_id: str
    name: str
    color: Optional[int] = None
    position: int = 0
    inherits_from: Optional[str] = None
    is_default: bool = False
    hoist: bool = False
    permissions: list[RolePermission] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Role:
        return cls(
            id=d["id"],
            space_id=d.get("space_id", ""),
            name=d["name"],
            color=d.get("color"),
            position=d.get("position", 0),
            inherits_from=d.get("inherits_from"),
            is_default=d.get("is_default", False),
            hoist=d.get("hoist", False),
            permissions=[
                RolePermission.from_dict(p) for p in d.get("permissions", [])
            ],
        )


@dataclass
class Channel:
    id: str
    space_id: str
    name: str
    channel_type: str = "text"
    topic: Optional[str] = None
    category_id: Optional[str] = None
    position: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> Channel:
        return cls(
            id=d["id"],
            space_id=d.get("space_id", ""),
            name=d["name"],
            channel_type=d.get("channel_type", "text"),
            topic=d.get("topic"),
            category_id=d.get("category_id"),
            position=d.get("position", 0),
        )


@dataclass
class ChannelCategory:
    id: str
    space_id: str
    name: str
    position: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> ChannelCategory:
        return cls(
            id=d["id"],
            space_id=d.get("space_id", ""),
            name=d["name"],
            position=d.get("position", 0),
        )


@dataclass
class Attachment:
    id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    url: str
    width: Optional[int] = None
    height: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> Attachment:
        return cls(
            id=d["id"],
            filename=d["filename"],
            original_filename=d.get("original_filename", d["filename"]),
            content_type=d.get("content_type", ""),
            size_bytes=d.get("size_bytes", 0),
            url=d["url"],
            width=d.get("width"),
            height=d.get("height"),
        )


@dataclass
class Embed:
    id: str
    url: str
    embed_type: str = "link"
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    site_name: Optional[str] = None
    color: Optional[int] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    provider_name: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> Embed:
        return cls(
            id=d.get("id", ""),
            url=d.get("url", ""),
            embed_type=d.get("embed_type", "link"),
            title=d.get("title"),
            description=d.get("description"),
            thumbnail_url=d.get("thumbnail_url"),
            site_name=d.get("site_name"),
            color=d.get("color"),
            image_url=d.get("image_url"),
            video_url=d.get("video_url"),
            provider_name=d.get("provider_name"),
        )


@dataclass
class Reaction:
    emoji: str
    count: int
    user_reacted: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> Reaction:
        return cls(
            emoji=d["emoji"],
            count=d["count"],
            user_reacted=d.get("user_reacted", False),
        )


@dataclass
class Message:
    id: str
    channel_id: str
    content: str
    author: User
    space_id: Optional[str] = None
    created_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    reply_to: Optional[str] = None
    ping_author: bool = False
    embeds: list[Embed] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    reactions: list[Reaction] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict, *, space_id: str | None = None) -> Message:
        author_data = d.get("author", {})
        return cls(
            id=d["id"],
            channel_id=d.get("channel_id", ""),
            content=d.get("content", ""),
            author=User.from_dict(author_data),
            space_id=space_id,
            created_at=_parse_dt(d.get("created_at")),
            edited_at=_parse_dt(d.get("edited_at")),
            reply_to=d.get("reply_to"),
            ping_author=d.get("ping_author", False),
            embeds=[Embed.from_dict(e) for e in d.get("embeds", [])],
            attachments=[
                Attachment.from_dict(a) for a in d.get("attachments", [])
            ],
            reactions=[
                Reaction.from_dict(r) for r in d.get("reactions", [])
            ],
        )


@dataclass
class CustomEmoji:
    id: str
    space_id: str
    name: str
    image_url: str
    uploaded_by: str = ""
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: dict) -> CustomEmoji:
        return cls(
            id=d["id"],
            space_id=d.get("space_id", ""),
            name=d["name"],
            image_url=d["image_url"],
            uploaded_by=d.get("uploaded_by", ""),
            created_at=_parse_dt(d.get("created_at")),
        )


@dataclass
class Space:
    id: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    owner_id: Optional[str] = None
    is_public: bool = False
    channels: Optional[list[Channel]] = None
    members: Optional[list[Member]] = None
    roles: Optional[list[Role]] = None
    categories: Optional[list[ChannelCategory]] = None
    custom_emojis: Optional[list[CustomEmoji]] = None

    @classmethod
    def from_dict(cls, d: dict) -> Space:
        channels = d.get("channels")
        members = d.get("members")
        roles = d.get("roles")
        categories = d.get("categories")
        custom_emojis = d.get("custom_emojis")
        return cls(
            id=d["id"],
            name=d["name"],
            description=d.get("description"),
            icon_url=d.get("icon_url"),
            owner_id=d.get("owner_id"),
            is_public=d.get("is_public", False),
            channels=[Channel.from_dict(c) for c in channels] if channels is not None else None,
            members=[Member.from_dict(m) for m in members] if members is not None else None,
            roles=[Role.from_dict(r) for r in roles] if roles is not None else None,
            categories=[ChannelCategory.from_dict(c) for c in categories] if categories is not None else None,
            custom_emojis=[CustomEmoji.from_dict(e) for e in custom_emojis] if custom_emojis is not None else None,
        )


@dataclass
class Invite:
    id: str
    space_id: str
    code: str
    created_by: str = ""
    max_uses: Optional[int] = None
    use_count: int = 0
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    url: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Invite:
        created_by = d.get("created_by", "")
        if isinstance(created_by, dict):
            created_by = created_by.get("id", "")
        return cls(
            id=d["id"],
            space_id=d.get("space_id", ""),
            code=d["code"],
            created_by=created_by,
            max_uses=d.get("max_uses"),
            use_count=d.get("use_count", 0),
            expires_at=_parse_dt(d.get("expires_at")),
            created_at=_parse_dt(d.get("created_at")),
            url=d.get("url", ""),
        )
