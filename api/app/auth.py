import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException

# Must match TOKEN_KEY_CONTEXT in src/app/session-token/route.ts
TOKEN_KEY_CONTEXT = b"ai-analyst-api-token"


def _signing_key() -> bytes | None:
    """
    Derives the API token signing key from AUTH_SECRET (shared with NextAuth),
    so the same secret isn't used directly for two different purposes.
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        return None
    return hmac.new(secret.encode(), TOKEN_KEY_CONTEXT, hashlib.sha256).digest()


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def verify_token(token: str) -> dict | None:
    """
    Verifies an HS256 JWT issued by the Next.js /session-token route.
    Returns the payload if the signature is valid and it hasn't expired.
    """
    key = _signing_key()
    if key is None:
        return None

    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            return None

        expected = hmac.new(key, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(signature_b64)):
            return None

        payload = json.loads(_b64url_decode(payload_b64))
        if not isinstance(payload.get("exp"), (int, float)) or payload["exp"] < time.time():
            return None

        allowed_email = os.getenv("ALLOWED_USER_EMAIL")
        if allowed_email and payload.get("sub") != allowed_email:
            return None

        return payload
    except Exception:
        return None


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    """
    FastAPI dependency: rejects requests without a valid Bearer token.
    """
    if _signing_key() is None:
        print("Error: AUTH_SECRET is not set; rejecting API request.")
        raise HTTPException(status_code=500, detail="Server authentication is not configured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})

    payload = verify_token(authorization[len("Bearer "):])
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})

    return payload
