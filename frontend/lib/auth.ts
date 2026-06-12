import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import { fetchAPI } from "@/lib/api";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const res = await fetchAPI<{ access_token: string }>("/auth/login", {
            method: "POST",
            body: { email: credentials.email, password: credentials.password },
          });
          return { id: res.access_token, accessToken: res.access_token };
        } catch {
          return null;
        }
      },
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      if (account?.provider === "google") {
        if (!account.id_token) return token;
        try {
          const res = await fetchAPI<{ access_token: string }>("/auth/google", {
            method: "POST",
            body: { token: account.id_token },
          });
          token.accessToken = res.access_token;
        } catch {
          // token.accessToken remains undefined; session will reflect this
        }
      } else if (user?.accessToken) {
        token.accessToken = user.accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
