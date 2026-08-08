"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  Wallet, Plus, ArrowRight, RefreshCw,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fetchEscrows, type EscrowItem } from "@/hooks/use-escrows";

function statusBadge(status: string) {
  const map: Record<string, { label: string; className: string }> = {
    draft: { label: "Draft", className: "bg-slate-600/20 text-slate-300 border-slate-600/30" },
    awaiting_funding: { label: "Awaiting funding", className: "bg-amber-600/20 text-amber-300 border-amber-600/30" },
    funded: { label: "Funded", className: "bg-green-600/20 text-green-300 border-green-600/30" },
    active: { label: "Active", className: "bg-blue-600/20 text-blue-300 border-blue-600/30" },
    release_pending: { label: "Releasing", className: "bg-purple-600/20 text-purple-300 border-purple-600/30" },
    released: { label: "Settled", className: "bg-emerald-600/20 text-emerald-300 border-emerald-600/30" },
    cancelled: { label: "Cancelled", className: "bg-red-600/20 text-red-300 border-red-600/30" },
    refunded: { label: "Refunded", className: "bg-orange-600/20 text-orange-300 border-orange-600/30" },
    disputed: { label: "Disputed", className: "bg-red-600/20 text-red-300 border-red-600/30" },
    failed: { label: "Failed", className: "bg-red-600/20 text-red-300 border-red-600/30" },
    expired: { label: "Expired", className: "bg-slate-600/20 text-slate-300 border-slate-600/30" },
  };
  const info = map[status] ?? { label: status, className: "bg-slate-600/20 text-slate-300 border-slate-600/30" };
  return (
    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${info.className}`}>
      {info.label}
    </Badge>
  );
}

const activeStatuses = ["draft", "awaiting_funding", "funded", "active", "release_pending"];

export default function EscrowsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const [escrows, setEscrows] = useState<EscrowItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session?.accessToken) return;
    setLoading(true);
    fetchEscrows(session.accessToken)
      .then((data) => setEscrows(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/set-state-in-effect
  }, [session?.accessToken]);

  const refresh = () => {
    if (!session?.accessToken) return;
    setLoading(true);
    fetchEscrows(session.accessToken)
      .then((data) => setEscrows(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const active = escrows.filter((e) => activeStatuses.includes(e.status));
  const past = escrows.filter((e) => !activeStatuses.includes(e.status));

  const agentLabel = (e: EscrowItem) => {
    const parts = e.agent_coordinate.split(":");
    return parts[2] && parts[2] !== "escrow" ? parts[2] : parts[1]?.slice(0, 10) ?? "Agent";
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Escrows</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track your escrow sessions — funding, releases, and settlements.
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={refresh} variant="outline" size="sm" className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button onClick={() => router.push("/dashboard/escrows/create")} size="sm" className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            New escrow
          </Button>
        </div>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">Loading escrows...</p>
          </CardContent>
        </Card>
      )}

      {!loading && active.length === 0 && past.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Wallet className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium text-muted-foreground">No escrows yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Create an escrow from the Agent page or click New escrow above.
            </p>
          </CardContent>
        </Card>
      )}

      {active.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Active escrows</h2>
          <div className="space-y-3">
            {active.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => router.push(`/dashboard/escrows/${e.id}`)}
                className="w-full text-left rounded-lg border border-slate-700 bg-slate-900/60 p-4 transition-colors hover:border-slate-500 hover:bg-slate-900/80"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-100">
                      {agentLabel(e)} &middot; {e.amount_sats.toLocaleString()} sats
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      Rail: {e.rail}
                      {e.release_policy.release_trigger
                        ? ` · Release: ${e.release_policy.release_trigger}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {statusBadge(e.status)}
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-500 mb-3">Past escrows</h2>
          <div className="space-y-2">
            {past.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => router.push(`/dashboard/escrows/${e.id}`)}
                className="w-full text-left rounded-lg border border-slate-800 bg-slate-950/40 p-3 transition-colors hover:border-slate-700"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-slate-400">
                    {agentLabel(e)} &middot; {e.amount_sats.toLocaleString()} sats
                  </p>
                  <div className="flex items-center gap-2">
                    {statusBadge(e.status)}
                    <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
