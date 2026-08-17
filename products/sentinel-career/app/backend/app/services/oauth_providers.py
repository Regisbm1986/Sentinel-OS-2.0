from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

_DEFAULT_TIMEOUT = 10

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class OAuthExchangeError(RuntimeError):
    """Raised when the OAuth token exchange fails."""


@dataclass(frozen=True)
class OAuthUser:
    provider: str
    subject: str
    email: str
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]


def _decode_jwt_payload(id_token: str) -> Dict[str, Any]:
    try:
        _header, payload_segment, _signature = id_token.split(".", 2)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise OAuthExchangeError("Formato inválido do id_token.") from exc

    padding = '=' * (-len(payload_segment) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_segment + padding)
    except (ValueError, TypeError) as exc:
        raise OAuthExchangeError("Falha ao decodificar id_token.") from exc

    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise OAuthExchangeError("id_token inválido.") from exc


class GoogleOAuthClient:
    def exchange_code(
        self,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        response = requests.post(_GOOGLE_TOKEN_URL, data=data, timeout=_DEFAULT_TIMEOUT)
        if response.status_code != 200:
            raise OAuthExchangeError("Falha ao trocar código de autorização com Google.")
        payload = response.json()
        if "id_token" not in payload or "access_token" not in payload:
            raise OAuthExchangeError("Resposta do Google sem tokens esperados.")
        return payload

    def fetch_userinfo(self, access_token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(_GOOGLE_USERINFO_URL, headers=headers, timeout=_DEFAULT_TIMEOUT)
        if response.status_code != 200:
            raise OAuthExchangeError("Falha ao consultar dados do usuário Google.")
        return response.json()

    def build_user(
        self,
        *,
        id_token: str,
        userinfo: Dict[str, Any],
        client_id: str,
        expected_nonce: str,
    ) -> OAuthUser:
        claims = _decode_jwt_payload(id_token)
        issuer = claims.get("iss")
        if issuer not in ("https://accounts.google.com", "accounts.google.com"):
            raise OAuthExchangeError("Issuer inválido retornado pelo Google.")

        audience = claims.get("aud")
        if audience != client_id:
            if isinstance(audience, list) and client_id in audience:
                pass
            else:
                raise OAuthExchangeError("Audience do id_token não corresponde ao client_id configurado.")

        nonce = claims.get("nonce")
        if not nonce or nonce != expected_nonce:
            raise OAuthExchangeError("Nonce inválido ou ausente no id_token do Google.")

        expires_at = claims.get("exp")
        if expires_at and time.time() > float(expires_at):
            raise OAuthExchangeError("id_token do Google expirado.")

        email = claims.get("email") or userinfo.get("email")
        if not email:
            raise OAuthExchangeError("Resposta do Google não contém e-mail do usuário.")

        email_verified_claim = claims.get("email_verified")
        email_verified_info = userinfo.get("email_verified")
        email_verified = bool(email_verified_claim or email_verified_info)
        if isinstance(email_verified_claim, str):
            email_verified = email_verified_claim.lower() == "true"
        if isinstance(email_verified_info, str):
            email_verified = email_verified_info.lower() == "true"

        if not email_verified:
            raise OAuthExchangeError("E-mail do Google não verificado.")

        subject = claims.get("sub")
        if not subject:
            raise OAuthExchangeError("id_token do Google sem identificador de usuário.")

        full_name = userinfo.get("name") or claims.get("name")
        picture = userinfo.get("picture") or claims.get("picture")

        return OAuthUser(
            provider="google",
            subject=str(subject),
            email=email,
            email_verified=email_verified,
            name=full_name,
            picture=picture,
        )


google_oauth_client = GoogleOAuthClient()


