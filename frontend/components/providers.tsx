"use client";

import { SessionProvider, signOut } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";
import type { Session } from "next-auth";
import { ApiError } from "@/lib/api";

export function Providers({ children, session }: { children: React.ReactNode; session: Session | null }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" disableTransitionOnChange>
      <SessionProvider session={session}>
        <SWRConfig
          value={{
            onError: (err) => {
              // A rejected token (expired/invalid) means the session is dead —
              // sign out and send the organizer back to login instead of
              // leaving them stuck on a silently-failing dashboard.
              if (err instanceof ApiError && err.status === 401) {
                signOut({ callbackUrl: "/login" });
              }
            },
          }}
        >
          {children}
        </SWRConfig>
      </SessionProvider>
    </ThemeProvider>
  );
}
