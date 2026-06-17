"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Member { id: string; name: string }
interface Team { id: string; name: string; members: Member[] }

export function FindMyTeam({ allocationId }: { allocationId: string }) {
  const [email, setEmail] = useState("");
  const [team, setTeam] = useState<Team | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "notfound">("idle");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setState("loading");
    setTeam(null);
    try {
      const t = await fetchAPI<Team>(
        `/api/v1/public/allocations/${allocationId}/find-team`,
        { method: "POST", body: { email } }
      );
      setTeam(t);
      setState("idle");
    } catch {
      setState("notfound");
    }
  };

  return (
    <div className="rounded-lg border bg-white p-4 max-w-md mx-auto">
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input
          aria-label="Email"
          type="email"
          placeholder="Email you registered with"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <Button type="submit" disabled={state === "loading"}>
          {state === "loading" ? "Finding…" : "Find my team"}
        </Button>
      </form>
      {team && (
        <p className="text-sm mt-3">
          You&apos;re on <strong>{team.name}</strong> — with {team.members.map(m => m.name).join(", ")}.
        </p>
      )}
      {state === "notfound" && (
        <p className="text-sm text-muted-foreground mt-3">
          We couldn&apos;t find that email on this event. Check the address you registered with.
        </p>
      )}
    </div>
  );
}
