"use client";

import { useState, useEffect, Suspense } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  Shield, Zap, Loader2, ArrowLeft, ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { createEscrow } from "@/hooks/use-escrows";

function CreateEscrowForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: session } = useSession();
  const prefillAgent = searchParams.get("agent") ?? "";

  const [agentCoordinate, setAgentCoordinate] = useState(prefillAgent);
  const [amountSats, setAmountSats] = useState(100000);
  const [rail, setRail] = useState("lightning");
  const [creating, setCreating] = useState(false);

  const agentLabel = () => {
    const parts = agentCoordinate.split(":");
    return parts[2] && parts[2] !== "escrow" ? parts[2] : agentCoordinate.slice(0, 30) || "Agent";
  };

  const handleCreate = async () => {
    if (!session?.accessToken) return;
    if (!agentCoordinate.trim()) {
      toast.error("Enter an agent coordinate");
      return;
    }
    setCreating(true);
    try {
      const escrow = await createEscrow(session.accessToken, {
        agent_coordinate: agentCoordinate.trim(),
        amount_sats: amountSats,
        rail,
      });
      toast.success("Escrow created");
      router.push(`/dashboard/escrows/${escrow.id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create escrow");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-lg">
      <button
        type="button"
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </button>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {prefillAgent ? `Create escrow with ${agentLabel()}` : "Create escrow"}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Set up a new escrow session to hold funds until prize conditions are met.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="agent-coordinate">Agent coordinate</Label>
          <Input
            id="agent-coordinate"
            placeholder="30361:pubkey:identifier"
            value={agentCoordinate}
            onChange={(e) => setAgentCoordinate(e.target.value)}
            disabled={!!prefillAgent}
          />
          <p className="text-xs text-muted-foreground">
            The escrow agent&apos;s Nostr coordinate. Copy this from the Agent page.
          </p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="amount-sats">Amount (sats)</Label>
          <Input
            id="amount-sats"
            type="number"
            min={1}
            value={amountSats}
            onChange={(e) => setAmountSats(Math.max(1, parseInt(e.target.value, 10) || 0))}
          />
        </div>

        <div className="space-y-2">
          <Label>Payment rail</Label>
          <div className="flex rounded-lg border border-slate-700 bg-slate-950/35 p-1">
            {(["lightning", "bitcoin", "spark"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRail(r)}
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors ${
                  rail === r
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {r === "lightning" && <Zap className="inline h-3.5 w-3.5 mr-1.5 text-amber-400" />}
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Review card */}
      <Card className="border-slate-700 bg-slate-900/60">
        <CardContent className="p-4 space-y-2.5">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">Review</p>
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Agent</span>
              <span className="text-slate-200">{agentLabel()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Amount</span>
              <span className="text-slate-200 font-mono">{amountSats.toLocaleString()} sats</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rail</span>
              <span className="text-slate-200 capitalize">{rail}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Release</span>
              <span className="text-slate-200 text-xs">Allocation published</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Refund</span>
              <span className="text-slate-200 text-xs">48h after event / cancel</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button
          className="flex-1 gap-1.5"
          onClick={handleCreate}
          disabled={creating || !agentCoordinate.trim()}
        >
          {creating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Shield className="h-4 w-4" />
          )}
          Create escrow
        </Button>
      </div>
    </div>
  );
}

export default function CreateEscrowPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6 max-w-lg">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    }>
      <CreateEscrowForm />
    </Suspense>
  );
}
