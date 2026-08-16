from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Optional

from urllib.parse import quote, unquote

_STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class OAuthStateResult:
    token: str
    state_value: str
    nonce: str
    next_path: Optional[str]


@dataclass(frozen=True)
class OAuthStateData:
    provider: str
    nonce: str
    next_path: Optional[str]
    created_at: float


class OAuthStateStore:
    def __init__(self, ttl_seconds: int = _STATE_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._states: dict[str, OAuthStateData] = {}
        self._lock = threading.Lock()

    def issue(self, provider: str, base_state: str, next_path: Optional[str]) -> OAuthStateResult:
        token = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        created_at = time.time()

        state_value = base_state
        state_value += f"|token={token}"
        if next_path:
            encoded_next = quote(next_path, safe="/?:=&%")
            state_value += f"|next={encoded_next}"

        record = OAuthStateData(provider=provider, nonce=nonce, next_path=next_path, created_at=created_at)
        with self._lock:
            self._cleanup_locked()
            self._states[token] = record

        return OAuthStateResult(token=token, state_value=state_value, nonce=nonce, next_path=next_path)

    def consume(self, provider: str, base_state: str, received_state: Optional[str]) -> OAuthStateData:
        if not received_state:
            raise ValueError("missing_state")

        segments = received_state.split("|")
        if not segments or segments[0] != base_state:
            raise ValueError("invalid_state_base")

        token: Optional[str] = None
        next_override: Optional[str] = None
        for segment in segments[1:]:
            if segment.startswith("token="):
                token = segment.partition("=")[2] or None
            elif segment.startswith("next="):
                raw_next = segment.partition("=")[2]
                if raw_next:
                    next_override = unquote(raw_next)

        if not token:
            raise ValueError("missing_state_token")

        with self._lock:
            self._cleanup_locked()
            record = self._states.pop(token, None)

        if record is None:
            raise ValueError("unknown_state_token")
        if record.provider != provider:
            raise ValueError("state_provider_mismatch")
        if time.time() - record.created_at > self._ttl_seconds:
            raise ValueError("state_expired")

        if next_override:
            return OAuthStateData(provider=record.provider, nonce=record.nonce, next_path=next_override, created_at=record.created_at)
        return record

    def _cleanup_locked(self) -> None:
        if not self._states:
            return
        now = time.time()
        expired = [token for token, record in self._states.items() if now - record.created_at > self._ttl_seconds]
        for token in expired:
            self._states.pop(token, None)


oauth_state_store = OAuthStateStore()
