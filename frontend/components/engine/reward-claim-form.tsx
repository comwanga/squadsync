"use client";

import { useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { submitRewardClaim, type PublicRewardClaim } from "@/hooks/use-allocation";

const LIGHTNING_ADDRESS_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function RewardClaimForm({ claim }: { claim: PublicRewardClaim }) {
  const [address, setAddress] = useState(claim.lightning_address ?? "");
  const [current, setCurrent] = useState(claim);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const alreadyPaid = current.status === "paid";
  const alreadyClaimed = current.status === "claimed";
  const expired = current.status === "expired";

  const submit = async () => {
    const trimmed = address.trim();
    setError(null);
    if (!LIGHTNING_ADDRESS_RE.test(trimmed)) {
      setError("Use a Lightning Address like name@example.com.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await submitRewardClaim(current.token, trimmed);
      setCurrent(updated);
      toast.success("Reward claim submitted");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Could not submit claim";
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (alreadyPaid) {
    return (
      <div className="flex flex-col items-center gap-3 py-6 text-center">
        <CheckCircle2 className="h-12 w-12 text-green-600" />
        <p className="text-lg font-semibold">Reward paid</p>
        <p className="text-sm text-muted-foreground">
          This reward has already been sent.
        </p>
      </div>
    );
  }

  if (expired) {
    return (
      <div className="py-6 text-center">
        <p className="text-lg font-semibold">Claim expired</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask the organizer to create a fresh claim QR.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-md border bg-slate-50 p-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-muted-foreground">Recipient</span>
          <span className="font-medium">{current.participant_name}</span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="text-muted-foreground">Team</span>
          <span className="font-medium">{current.team_name}</span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="text-muted-foreground">Reward</span>
          <span className="font-mono font-medium">{current.amount_sats} sats</span>
        </div>
      </div>

      {alreadyClaimed && (
        <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Claim received. The organizer can now send your reward.
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="lightning-address">Lightning Address</Label>
        <Input
          id="lightning-address"
          inputMode="email"
          autoComplete="email"
          placeholder="name@example.com"
          value={address}
          onChange={e => setAddress(e.target.value)}
          disabled={submitting}
        />
        <p className="text-xs text-muted-foreground">
          This is where your reward will be sent.
        </p>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <Button type="button" className="w-full" size="lg" onClick={submit} disabled={submitting}>
        <Zap className="mr-2 h-4 w-4" />
        {submitting ? "Submitting..." : alreadyClaimed ? "Update claim" : "Claim reward"}
      </Button>
    </div>
  );
}
