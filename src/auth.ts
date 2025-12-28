import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { handlers, auth, signIn, signOut } = NextAuth({
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
})
