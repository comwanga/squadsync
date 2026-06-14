import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { fetchAPI } from "@/lib/api";

export const { handlers, auth, signIn, signOut } = NextAuth({
  // Keep the NextAuth session lifetime in step with the backend JWT
  // (ACCESS_TOKEN_EXPIRE_MINUTES = 1440) so they expire together.
  session: { maxAge: 60 * 60 * 24 },
  providers: [
    Credentials({
      credentials: {
        pubkey: { label: "Public Key", type: "text" },
        signedEvent: { label: "Signed Event", type: "text" },
      },
      async authorize(credentials) {
        try {
          const res = await fetchAPI<{ access_token: string }>("/auth/nostr", {
            method: "POST",
            body: {
              pubkey: credentials.pubkey,
              event: JSON.parse(credentials.signedEvent as string),
            },
          });
          return {
            id: res.access_token,
            accessToken: res.access_token,
            pubkey: credentials.pubkey as string,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user?.accessToken) {
        token.accessToken = user.accessToken;
        token.pubkey = user.pubkey;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.pubkey = token.pubkey as string | undefined;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
