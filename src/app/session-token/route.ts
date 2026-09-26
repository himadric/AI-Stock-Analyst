import { createHmac } from "crypto";
import { NextResponse } from "next/server";
import { auth } from "@/auth";

// Must match TOKEN_KEY_CONTEXT in api/app/auth.py
const TOKEN_KEY_CONTEXT = "ai-analyst-api-token";
const TOKEN_TTL_SECONDS = 60 * 60;

export const dynamic = "force-dynamic";

function base64url(input: string | Buffer) {
  return Buffer.from(input).toString("base64url");
}

// Issues a short-lived HS256 JWT that the FastAPI backend verifies on every request.
export async function GET() {
  const session = await auth();
  const email = session?.user?.email;

  if (!email || email !== process.env.ALLOWED_USER_EMAIL) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const secret = process.env.AUTH_SECRET;
  if (!secret) {
    return NextResponse.json({ error: "Server authentication is not configured" }, { status: 500 });
  }

  const key = createHmac("sha256", secret).update(TOKEN_KEY_CONTEXT).digest();
  const expiresAt = Math.floor(Date.now() / 1000) + TOKEN_TTL_SECONDS;

  const header = base64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64url(JSON.stringify({ sub: email, exp: expiresAt }));
  const signature = base64url(createHmac("sha256", key).update(`${header}.${payload}`).digest());

  return NextResponse.json(
    { token: `${header}.${payload}.${signature}`, expiresAt },
    { headers: { "Cache-Control": "no-store" } }
  );
}
