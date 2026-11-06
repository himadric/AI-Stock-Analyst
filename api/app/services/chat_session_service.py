"""
Persists the main chat widget's conversation history to MongoDB, one
growing document per session (see docs/plans/persist-chat-history-plan.md).
Scope is the main chat (POST /api/agent/chat) only - multi_agent.py's
/multi_analysis flow stays unsaved, same as context compaction and
reflection already being "main chat only" features.

Mirrors PortfolioService's shape: a plain class, a _serialize helper that
converts Mongo's _id to a string id and re-attaches UTC tzinfo to the
naive datetimes pymongo returns (BSON strips tzinfo, always UTC - the same
fix watchlist.py's get_watchlist_report() already needed once).

No user_id field, consistent with every other collection in this app
(single-user, no multi-tenant convention anywhere).
"""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.db import db

IMAGE_PLACEHOLDER = "[image omitted from stored history]"


def _strip_images(content):
    """
    A user message's content is either a plain string or a list of
    Anthropic content blocks (text + image, for a pasted image - see
    agent.py's ChatMessage). An image block's real base64 payload is never
    persisted - it's replaced with a short placeholder so a never-expiring,
    ever-growing session document stays bounded. Plain strings pass through
    unchanged.
    """
    if not isinstance(content, list):
        return content

    stripped = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "image":
            block = dict(block)
            source = dict(block.get("source") or {})
            source["data"] = IMAGE_PLACEHOLDER
            block["source"] = source
            stripped.append(block)
        else:
            stripped.append(block)
    return stripped


def _derive_title(first_user_content) -> str:
    """
    First ~60 chars of the first user message's text, whitespace
    collapsed. Falls back to "Chat with image" if that first message is
    image-only content blocks with no text at all.
    """
    if isinstance(first_user_content, str):
        text = first_user_content
    elif isinstance(first_user_content, list):
        text = " ".join(
            b.get("text", "") for b in first_user_content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        text = ""

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Chat with image"

    if len(text) > 60:
        return text[:60].rstrip() + "..."
    return text


def _as_utc(value):
    return value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) and value.tzinfo is None else value


class ChatSessionService:
    def _serialize(self, doc: dict) -> dict:
        # pymongo returns naive datetimes (BSON strips tzinfo, always UTC) -
        # re-attach it everywhere one appears, top-level AND inside each
        # stored message, or FastAPI serializes an offset-less ISO string
        # the browser misreads as local time (the exact bug watchlist.py's
        # get_watchlist_report() already hit once - this must not repeat it
        # half-fixed, even though the frontend doesn't read per-message
        # timestamps yet).
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["created_at"] = _as_utc(doc.get("created_at"))
        doc["updated_at"] = _as_utc(doc.get("updated_at"))
        if doc.get("messages"):
            doc["messages"] = [
                {**m, "created_at": _as_utc(m.get("created_at"))} for m in doc["messages"]
            ]
        return doc

    def create_session(self, first_user_content) -> str:
        """Creates a new, empty session and returns its id as a string."""
        now = datetime.now(timezone.utc)
        doc = {
            "title": _derive_title(first_user_content),
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        result = db.get_db().chat_sessions.insert_one(doc)
        return str(result.inserted_id)

    def append_turn(self, session_id: str, user_entry: dict, assistant_entry: dict) -> None:
        """
        Appends one user+assistant turn to an existing session's messages
        array in a single update, stamping both entries' created_at and
        bumping the session's updated_at. The user entry's content is
        stripped of any real pasted-image data before storing.
        """
        try:
            oid = ObjectId(session_id)
        except (InvalidId, TypeError):
            return

        now = datetime.now(timezone.utc)
        user_entry = dict(user_entry)
        user_entry["content"] = _strip_images(user_entry.get("content"))
        user_entry["created_at"] = now
        assistant_entry = dict(assistant_entry)
        assistant_entry["created_at"] = now

        db.get_db().chat_sessions.update_one(
            {"_id": oid},
            {
                "$push": {"messages": {"$each": [user_entry, assistant_entry]}},
                "$set": {"updated_at": now},
            },
        )

    def list_sessions(self) -> list[dict]:
        """Cheap listing for the sidebar - excludes the messages array, sorted most-recent-first."""
        cursor = db.get_db().chat_sessions.find(
            {}, {"title": 1, "created_at": 1, "updated_at": 1}
        ).sort("updated_at", -1)
        return [self._serialize(doc) for doc in cursor]

    def get_session(self, session_id: str) -> dict | None:
        """Full transcript, serialized. None on a missing doc or a malformed id."""
        try:
            oid = ObjectId(session_id)
        except (InvalidId, TypeError):
            return None

        doc = db.get_db().chat_sessions.find_one({"_id": oid})
        return self._serialize(doc) if doc else None

    def delete_session(self, session_id: str) -> bool:
        try:
            oid = ObjectId(session_id)
        except (InvalidId, TypeError):
            return False

        result = db.get_db().chat_sessions.delete_one({"_id": oid})
        return result.deleted_count > 0


chat_session_service = ChatSessionService()
