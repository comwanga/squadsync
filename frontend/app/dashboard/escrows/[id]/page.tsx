"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Zap, Loader2, ArrowLeft, Copy, Check,
  Wallet, CircleDot, CircleCheck, XCircle, Eye, EyeOff,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  fetchEscrow, activateEscrow, fundEscrow, confirmFunded, cancelEscrow,
  type Escrow,
} from "@/hooks/use-escrows";
import { payWithNwc } from "@/lib/lightning";

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

export default function EscrowDetailPage() {
  const router = useRouter();
  const params = useParams();
  const { data: session } = useSession();
  const escrowId = params.id as string;

  const [escrow, setEscrow] = useState<Escrow | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  // NWC wallet
  const [nwcInput, setNwcInput] = useState("");
  const [showNwc, setShowNwc] = useState(false);
  const [fundingRequest, setFundingRequest] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Confirm funded dialog
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    if (!session?.accessToken) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetchEscrow(session.accessToken, escrowId)
      .then((data) => { setEscrow(data); setFundingRequest(data.funding_request); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [session?.accessToken, escrowId]);

  if (loading) {
    return (
      <div className="max-w-lg">
        <p className="text-sm text-muted-foreground">Loading escrow...</p>
      </div>
    );
  }

  if (!escrow) {
    return (
      <div className="max-w-lg">
        <p className="text-sm text-muted-foreground">Escrow not found.</p>
      </div>
    );
  }

  const agentLabel = () => {
    const parts = escrow.agent_coordinate.split(":");
    return parts[2] && parts[2] !== "escrow" ? parts[2] : parts[1]?.slice(0, 10) ?? "Agent";
  };

  const handleActivate = async () => {
    if (!session?.accessToken) return;
    setActing(true);
    try {
      const updated = await activateEscrow(session.accessToken, escrowId);
      setEscrow(updated);
      toast.success("Escrow activated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to activate escrow");
    } finally {
      setActing(false);
    }
  };

  const handleFund = async () => {
    if (!session?.accessToken) return;
    setActing(true);
    try {
      const updated = await fundEscrow(
        session.accessToken,
        escrowId,
        nwcInput.trim() || undefined,
      );
      setEscrow(updated);
      setFundingRequest(updated.funding_request);
      toast.success("Funding request generated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to generate funding request");
    } finally {
      setActing(false);
    }
  };

  const handlePayWithNwc = async () => {
    if (!session?.accessToken || !fundingRequest) return;
    setActing(true);
    try {
      await payWithNwc(escrow.nwc_uri!, fundingRequest);
      const updated = await confirmFunded(session.accessToken, escrowId);
      setEscrow(updated);
      toast.success("Payment sent and escrow funded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setActing(false);
    }
  };

  const handleMarkFunded = async () => {
    if (!session?.accessToken) return;
    setActing(true);
    try {
      const updated = await confirmFunded(session.accessToken, escrowId);
      setEscrow(updated);
      setConfirmOpen(false);
      toast.success("Escrow marked as funded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to update escrow");
    } finally {
      setActing(false);
    }
  };

  const handleCancel = async () => {
    if (!session?.accessToken) return;
    setActing(true);
    try {
      const updated = await cancelEscrow(session.accessToken, escrowId);
      setEscrow(updated);
      toast.success("Escrow cancelled");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to cancel escrow");
    } finally {
      setActing(false);
    }
  };

  const copyText = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isDraft = escrow.status === "draft";
  const needsFunding = escrow.status === "awaiting_funding";
  const isFunded = escrow.status === "funded";
  const isSettled = escrow.status === "released";
  const isTerminal = ["released", "cancelled", "refunded", "failed", "expired"].includes(escrow.status);

  return (
    <div className="space-y-6 max-w-lg">
      <button
        type="button"
        onClick={() => router.push("/dashboard/escrows")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Escrows
      </button>

      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight">
            {agentLabel()} &middot; {escrow.amount_sats.toLocaleString()} sats
          </h1>
          {statusBadge(escrow.status)}
        </div>
        <p className="text-sm text-muted-foreground mt-1 capitalize">
          {escrow.rail} escrow
        </p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-1.5">
        {(["draft", "awaiting_funding", "funded", "released"] as const).map((s, i) => {
          const completed = escrow.status === "released" || (
            s === "draft" ? !isDraft :
            s === "awaiting_funding" ? !isDraft && !needsFunding :
            s === "funded" ? isFunded || isSettled :
            isSettled
          );
          const current = escrow.status === s;
          return (
            <div key={s} className="flex items-center gap-1.5">
              {i > 0 && <div className={`w-4 h-px ${completed ? "bg-green-500" : "bg-slate-700"}`} />}
              {completed ? (
                <CircleCheck className="h-4 w-4 text-green-500" />
              ) : current ? (
                <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
              ) : (
                <CircleDot className="h-4 w-4 text-slate-600" />
              )}
            </div>
          );
        })}
      </div>

      {/* Escrow details */}
      <Card className="border-slate-700 bg-slate-900/60">
        <CardContent className="p-4 space-y-2.5 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Agent</span>
            <span className="text-slate-200 font-mono text-xs truncate ml-4 max-w-[200px]">
              {escrow.agent_coordinate}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Amount</span>
            <span className="text-slate-200 font-mono">{escrow.amount_sats.toLocaleString()} sats</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Rail</span>
            <span className="text-slate-200 capitalize">{escrow.rail}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Release</span>
            <span className="text-slate-200 text-xs text-right max-w-[200px]">
              {escrow.release_policy.release_trigger as string}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Refund</span>
            <span className="text-slate-200 text-xs text-right max-w-[200px]">
              {escrow.refund_policy.refund_trigger as string}
            </span>
          </div>
          {escrow.funded_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Funded</span>
              <span className="text-slate-400 text-xs">
                {new Date(escrow.funded_at).toLocaleDateString()}
              </span>
            </div>
          )}
          {escrow.released_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Released</span>
              <span className="text-slate-400 text-xs">
                {new Date(escrow.released_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Draft: activate */}
      {isDraft && (
        <Card className="border-amber-400/40 bg-amber-50/10 dark:bg-amber-950/20">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium text-amber-300">This escrow is a draft</p>
            <p className="text-xs text-muted-foreground">
              Activate it to generate a funding request and begin the escrow process.
            </p>
            <div className="flex gap-2">
              <Button onClick={handleActivate} disabled={acting} className="gap-1.5 flex-1">
                {acting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                Activate escrow
              </Button>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={acting}
                className="flex-1"
              >
                <XCircle className="h-4 w-4 mr-1.5" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Awaiting funding: show funding UI */}
      {needsFunding && (
        <div className="space-y-4">
          <Card className="border-blue-400/40 bg-blue-50/10 dark:bg-blue-950/20">
            <CardContent className="p-4 space-y-3">
              <p className="text-sm font-medium text-blue-300">Fund this escrow</p>
              <p className="text-xs text-muted-foreground">
                {escrow.amount_sats.toLocaleString()} sats · {escrow.rail}
              </p>

              {fundingRequest ? (
                <>
                  {/* NWC pay button */}
                  {escrow.nwc_uri && (
                    <Button
                      onClick={handlePayWithNwc}
                      disabled={acting}
                      className="gap-1.5 w-full"
                    >
                      {acting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Wallet className="h-4 w-4" />
                      )}
                      Pay {escrow.amount_sats.toLocaleString()} sats
                    </Button>
                  )}

                  {/* Manual payment */}
                  <div className="space-y-2 rounded-md border border-slate-700 bg-slate-950/35 p-3">
                    <p className="text-xs text-muted-foreground">Or pay manually</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-xs break-all text-slate-300 bg-slate-900/80 p-2 rounded">
                        {fundingRequest}
                      </code>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={() => copyText(fundingRequest)}
                      >
                        {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
                      </Button>
                    </div>
                  </div>

                  {/* Mark as funded */}
                  <Button
                    variant="outline"
                    onClick={() => setConfirmOpen(true)}
                    disabled={acting}
                    className="w-full"
                  >
                    <CircleCheck className="h-4 w-4 mr-1.5" />
                    I&apos;ve paid — mark as funded
                  </Button>
                </>
              ) : (
                <>
                  {/* NWC connection */}
                  <div className="space-y-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="nwc-input">Wallet connection (optional)</Label>
                      <div className="flex gap-1.5">
                        <div className="relative flex-1">
                          <Input
                            id="nwc-input"
                            type={showNwc ? "text" : "password"}
                            autoComplete="off"
                            value={nwcInput}
                            onChange={(e) => setNwcInput(e.target.value)}
                            placeholder="nostr+walletconnect://..."
                            className="pr-8"
                          />
                          <button
                            type="button"
                            onClick={() => setShowNwc(!showNwc)}
                            className="absolute inset-y-0 right-2 flex items-center text-muted-foreground hover:text-foreground"
                          >
                            {showNwc ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Stays in this browser. Never reaches the server. Connect to pay with one click.
                      </p>
                    </div>
                  </div>

                  <Button onClick={handleFund} disabled={acting} className="gap-1.5 w-full">
                    {acting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                    Generate funding request
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={acting}
            className="w-full"
          >
            <XCircle className="h-4 w-4 mr-1.5" />
            Cancel escrow
          </Button>
        </div>
      )}

      {/* Funded */}
      {isFunded && (
        <Card className="border-green-400/40 bg-green-50/10 dark:bg-green-950/20">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <CircleCheck className="h-5 w-5 text-green-400" />
              <p className="text-sm font-medium text-green-300">Escrow funded</p>
            </div>
            <p className="text-xs text-muted-foreground">
              {escrow.amount_sats.toLocaleString()} sats locked. Waiting for allocation outcome.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Settled */}
      {isSettled && (
        <Card className="border-emerald-400/40 bg-emerald-50/10 dark:bg-emerald-950/20">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <CircleCheck className="h-5 w-5 text-emerald-400" />
              <p className="text-sm font-medium text-emerald-300">Escrow settled</p>
            </div>
            <p className="text-xs text-muted-foreground">
              {escrow.amount_sats.toLocaleString()} sats distributed. Funds have been released to recipients.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Other terminal states */}
      {isTerminal && !isSettled && (
        <Card className="border-slate-600/40 bg-slate-950/20">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-slate-400" />
              <p className="text-sm font-medium text-slate-300">
                {escrow.status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Confirm funded dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Mark as funded?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Only confirm if the agent has received your payment. This cannot be undone.
          </p>
          <div className="flex gap-2 pt-2">
            <Button variant="outline" className="flex-1" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button className="flex-1" onClick={handleMarkFunded} disabled={acting}>
              {acting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Confirm funded
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
