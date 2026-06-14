"use client";

import { useState, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { Bell, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogoMark } from "@/components/brand/logo";

function truncateNpub(npub: string): string {
  return `${npub.slice(0, 10)}…${npub.slice(-4)}`;
}

export function Topbar() {
  const { data: session } = useSession();
  const [npub, setNpub] = useState<string>("");

  useEffect(() => {
    if (session?.pubkey) {
      import("nostr-tools/nip19").then(({ npubEncode }) => {
        const encoded = npubEncode(session.pubkey!);
        setNpub(encoded);
      });
    }
  }, [session?.pubkey]);

  const displayId = npub ? truncateNpub(npub) : session?.pubkey?.slice(0, 12) ?? "…";

  return (
    <header className="h-16 border-b bg-white dark:bg-slate-900 dark:border-slate-700 flex items-center justify-between px-6">
      <LogoMark className="md:hidden h-8 w-8" />
      <div className="flex-1" />
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Bell className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">
                  {session?.pubkey?.[0]?.toUpperCase() ?? "N"}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem className="text-xs text-muted-foreground font-mono" disabled>
              {displayId}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => signOut({ callbackUrl: "/login" })}>
              <LogOut className="mr-2 h-4 w-4" />
              Disconnect
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
