import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { handlers, auth, signIn, signOut } = NextAuth({
  debug: true,
  providers: [Google],
  callbacks: {
    async signIn({ user }) {
      if (user.email === process.env.ALLOWED_USER_EMAIL) {
        return true
      }
      return false // Return false to deny access
    },
  },
  pages: {
    signIn: "/login",
  },
  cookies: {
    pkceCodeVerifier: {
      name: "next-auth.pkce.code_verifier",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
})
