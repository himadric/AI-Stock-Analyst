"""
Mints an API session token for eval runs in HTTP mode (see run_evals.py) -
needed because /session-token normally requires a real browser sign-in,
which isn't practical for a script.

Mirrors app/auth.py's exact signing scheme (same TOKEN_KEY_CONTEXT, same
HMAC-SHA256-derived key from AUTH_SECRET, same HS256/sub/exp shape
verify_token() expects) - the issuing side of the same scheme
src/app/session-token/route.ts implements in TypeScript. This is the same
manual-token approach used throughout this app's development for live
curl testing, promoted into a real, reusable function.
"""
import base64
import hashlib
import hmac
import json
import time

# Must match TOKEN_KEY_CONTEXT in api/app/auth.py and src/app/session-token/route.ts
TOKEN_KEY_CONTEXT = b"ai-analyst-api-token"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def mint_token(auth_secret: str, allowed_user_email: str, ttl_seconds: int = 3600) -> str:
    """Issues an HS256 JWT that api/app/auth.py's verify_token() will accept."""
    key = hmac.new(auth_secret.encode(), TOKEN_KEY_CONTEXT, hashlib.sha256).digest()

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": allowed_user_email, "exp": int(time.time()) + ttl_seconds}

    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signature = hmac.new(key, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()

    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"
