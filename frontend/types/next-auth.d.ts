import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    accessToken?: string;
    pubkey?: string;
  }
  interface Session {
    accessToken?: string;
    pubkey?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    pubkey?: string;
  }
}
