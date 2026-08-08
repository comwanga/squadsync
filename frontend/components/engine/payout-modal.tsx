"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import QRCode from "react-qr-code";
import { Zap, CheckCircle2, XCircle, QrCode, RefreshCw, Shield } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import {
  createPayout,
  createRewardClaims,
  preflightPayout,
  reportPayoutItemResult,
  reportPayoutItemFailed,
  markEscrowFunded,
  markEscrowReleased,
  fetchEscrowAgents,
  type Payout,
  type PayoutItem,
  type EscrowAgent,
  type RewardClaim,
  type Team,
} from "@/hooks/use-allocation";
import { resolveInvoice, payWithNwc } from "@/lib/lightning";

interface PayoutModalProps {
  team: Team;
  allocationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface PaymentAttempt {
  bolt11: string;
  preimage?: string;
}

export function PayoutModal({ team, allocationId, open, onOpenChange }: PayoutModalProps) {
  const { data: session } = useSession();
  const [payoutMode, setPayoutMode] = useState<"direct" | "escrow">("direct");
  const [totalSats, setTotalSats] = useState(2100);
  const [nwc, setNwc] = useState("");
  const [addresses, setAddresses] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [payout, setPayout] = useState<Payout | null>(null);
  const [preflight, setPreflight] = useState<string[]>([]);
  const [claims, setClaims] = useState<RewardClaim[]>([]);
  const [paymentAttempts, setPaymentAttempts] = useState<Record<string, PaymentAttempt>>({});
  const [escrowAgents, setEscrowAgents] = useState<EscrowAgent[] | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<EscrowAgent | null>(null);

  const n = team.members.length;
  const base = n > 0 ? Math.floor(totalSats / n) : 0;
  const rem = n > 0 ? totalSats % n : 0;

  useEffect(() => {
    if (open && payoutMode === "escrow" && escrowAgents === null) {
      fetchEscrowAgents()
        .then((res) => setEscrowAgents(res.agents))
        .catch(() => { toast.error("Could not load escrow agents"); setEscrowAgents([]); });
    }
  }, [open, payoutMode, escrowAgents]);

  const handleOpenChange = (o: boolean) => {
    if (!o && Object.keys(paymentAttempts).length > 0) {
      toast.error("Finish confirming the in-progress payments before closing.");
      return;
    }
    if (!o) {
      setNwc("");
      setPreflight([]);
      setClaims([]);
      setEscrowAgents(null);
    }
    onOpenChange(o);
  };

  const markLocal = (current: Payout, itemId: string, status: string, error: string): Payout => ({
    ...current,
    items: current.items.map(item => item.id === itemId ? { ...item, status, error } : item),
  });

  // Once a wallet attempt starts, retain and reuse that exact invoice. A reporting
  // failure must never be converted into a fresh payment attempt.
  const payItems = async (current: Payout, items: PayoutItem[]): Promise<Payout> => {
    const token = session!.accessToken!;
    for (const item of items) {
      const addr = addresses[item.participant_id]?.trim() || item.lightning_address;
      let attempt = paymentAttempts[item.id];
      try {
        if (!addr) throw new Error("missing lightning address");
        if (!attempt) {
          attempt = { bolt11: await resolveInvoice(addr, item.amount_sats) };
          setPaymentAttempts(previous => ({ ...previous, [item.id]: attempt! }));
        }
        if (!attempt.preimage) {
          attempt = { ...attempt, preimage: await payWithNwc(nwc, attempt.bolt11) };
          setPaymentAttempts(previous => ({ ...previous, [item.id]: attempt! }));
        }
        current = await reportPayoutItemResult(
          token, current.id, item.id, attempt.bolt11, attempt.preimage!
        );
        setPaymentAttempts(previous => {
          const next = { ...previous };
          delete next[item.id];
          return next;
        });
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        if (attempt) {
          current = markLocal(
            current,
            item.id,
            "pending",
            attempt.preimage
              ? `Payment completed; confirmation pending: ${message}`
              : `Wallet result uncertain; retrying will reuse the same invoice: ${message}`,
          );
        } else {
          try {
            current = await reportPayoutItemFailed(token, current.id, item.id, message);
          } catch {
            current = markLocal(current, item.id, "failed", message);
          }
        }
      }
      setPayout(current); // live per-member status
    }
    return current;
  };

  const handleSend = async () => {
    if (!session?.accessToken) return;
    setSending(true);
    try {
      const overrides: Record<string, string> = {};
      for (const [id, addr] of Object.entries(addresses)) {
        if (addr.trim()) overrides[id] = addr.trim();
      }
      let current = await createPayout(session.accessToken, allocationId, {
        team_id: team.id,
        total_sats: totalSats,
        addresses: Object.keys(overrides).length > 0 ? overrides : undefined,
        escrow_coordinate:
          payoutMode === "escrow" && selectedAgent
            ? selectedAgent.coordinate
            : undefined,
      });

      if (payoutMode === "escrow") {
        setPayout(current);
        toast.success("Escrow payout created. Deposit funds with the agent to continue.", {
          duration: 6000,
        });
      } else {
        setPayout(current);
        current = await payItems(current, current.items);
        if (current.status === "complete") toast.success("Payout complete");
        else toast.error("Some payments need attention");
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && (err.status === 422 || err.status === 409)) {
        toast.error(err.message);
      } else {
        toast.error(err instanceof Error ? err.message : "Payout failed");
      }
    } finally {
      setSending(false);
    }
  };

  const handleEscrowFunded = async () => {
    if (!session?.accessToken || !payout) return;
    setSending(true);
    try {
      const updated = await markEscrowFunded(session.accessToken, payout.id);
      setPayout(updated);
      toast.success("Escrow marked as funded");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update escrow status");
    } finally {
      setSending(false);
    }
  };

  const handleEscrowReleased = async () => {
    if (!session?.accessToken || !payout) return;
    setSending(true);
    try {
      const updated = await markEscrowReleased(session.accessToken, payout.id);
      setPayout(updated);
      toast.success("Escrow marked as released. Recipients have been paid.");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update escrow status");
    } finally {
      setSending(false);
    }
  };

  const runDryCheck = async () => {
    if (!session?.accessToken) return;
    const issues: string[] = [];
    try {
      const overrides: Record<string, string> = {};
      for (const [id, addr] of Object.entries(addresses)) {
        if (addr.trim()) overrides[id] = addr.trim();
      }
      const result = await preflightPayout(session.accessToken, allocationId, {
        team_id: team.id,
        total_sats: totalSats,
        addresses: Object.keys(overrides).length > 0 ? overrides : undefined,
      });
      issues.push(`Dry run passed for ${result.items.length} member${result.items.length === 1 ? "" : "s"}.`);
      issues.push(`Split total: ${result.items.reduce((sum, item) => sum + item.amount_sats, 0)} sats.`);
      if (!nwc.trim()) issues.push("Add a wallet connection before sending a real payout.");
    } catch (err: unknown) {
      issues.push(err instanceof Error ? err.message : "Dry run failed");
    }
    setPreflight(issues);
  };

  const generateClaimLinks = async () => {
    if (!session?.accessToken) return;
    setSending(true);
    try {
      const result = await createRewardClaims(session.accessToken, allocationId, {
        team_id: team.id,
        total_sats: totalSats,
      });
      setClaims(result.items);
      setAddresses(prev => {
        const next = { ...prev };
        for (const claim of result.items) {
          if (claim.lightning_address) next[claim.participant_id] = claim.lightning_address;
        }
        return next;
      });
      toast.success("Claim QR links ready");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Could not create claim links");
    } finally {
      setSending(false);
    }
  };

  const handleRetry = async () => {
    if (!session?.accessToken || !payout) return;
    setSending(true);
    try {
      const retryIds = new Set([
        ...Object.keys(paymentAttempts),
        ...payout.items.filter(item => item.status === "failed").map(item => item.id),
      ]);
      const current = await payItems(payout, payout.items.filter(item => retryIds.has(item.id)));
      if (current.status === "complete") toast.success("Retry complete");
      else toast.error("Some payments still need attention");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setSending(false);
    }
  };

  const canSend = !sending && (payoutMode === "escrow" ? !!selectedAgent : !!nwc) && totalSats >= n;
  const hasFailedItems = Object.keys(paymentAttempts).length > 0
    || payout?.items.some(item => item.status === "failed");
  const claimedCount = claims.filter(claim => claim.lightning_address).length;

  const isEscrowActive =
    payout?.escrow_status === "escrow_pending" ||
    payout?.escrow_status === "escrow_funded";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {payoutMode === "escrow" ? (
              <Shield className="h-4 w-4 text-blue-500" />
            ) : (
              <Zap className="h-4 w-4 text-amber-500" />
            )}
            Advanced Rewards - {team.name}
          </DialogTitle>
          <DialogDescription>
            Optional prize splitting for this team. This is not required to publish or share results.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Payout mode toggle */}
          {!payout && (
            <div className="flex rounded-lg border border-slate-700 bg-slate-950/35 p-1">
              <button
                type="button"
                onClick={() => setPayoutMode("direct")}
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  payoutMode === "direct"
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Zap className="inline h-3.5 w-3.5 mr-1.5" />
                Direct send
              </button>
              <button
                type="button"
                onClick={() => setPayoutMode("escrow")}
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  payoutMode === "escrow"
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Shield className="inline h-3.5 w-3.5 mr-1.5" />
                Use escrow agent
              </button>
            </div>
          )}

          {/* Escrow agent selection */}
          {payoutMode === "escrow" && !payout && !isEscrowActive && (
            <div className="space-y-2 rounded-md border border-blue-500/30 bg-blue-950/20 p-3">
              <p className="text-sm font-medium text-blue-300">Select an escrow agent</p>
              <p className="text-xs text-muted-foreground">
                Agents are discovered from the Nostr network. Select one to hold funds
                until prizes are released.
              </p>

              {escrowAgents === null && (
                <p className="text-xs text-muted-foreground">Loading agents from relays...</p>
              )}

              {escrowAgents !== null && escrowAgents.length === 0 && (
                <p className="text-xs text-amber-400">
                  No escrow agents found. Register yourself as an agent from the{" "}
                  <strong>Agent</strong> page, or use Direct send instead.
                </p>
              )}

              <div className="space-y-2 max-h-48 overflow-y-auto">
                {escrowAgents?.map((agent) => (
                  <button
                    key={agent.coordinate}
                    type="button"
                    onClick={() => setSelectedAgent(agent)}
                    className={`w-full min-w-0 text-left rounded-md border p-2.5 transition-colors overflow-hidden ${
                      selectedAgent?.coordinate === agent.coordinate
                        ? "border-blue-400 bg-blue-900/40"
                        : "border-slate-700 bg-slate-900/60 hover:border-slate-500"
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-100 truncate">
                      {agent.coordinate}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {agent.escrow_type} &middot; {agent.networks.join(", ")}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      Release: {agent.release_rules.release_trigger}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Total sats input */}
          <div className="space-y-1.5">
            <Label htmlFor="total-sats">Total prize (sats)</Label>
            <Input
              id="total-sats"
              type="number"
              min={n}
              value={totalSats}
              onChange={e => setTotalSats(Math.max(0, parseInt(e.target.value, 10) || 0))}
              disabled={!!payout}
            />
          </div>

          {/* Direct NWC wallet input (only in direct mode) */}
          {payoutMode === "direct" && !payout && (
            <div className="space-y-1.5">
              <Label htmlFor="nwc">Wallet connection string</Label>
              <Input
                id="nwc"
                type="password"
                autoComplete="off"
                value={nwc}
                onChange={e => setNwc(e.target.value)}
                placeholder="Paste wallet connection string"
                disabled={!!payout}
              />
              <p className="text-xs text-muted-foreground">
                Used only in this browser while sending. It is not stored and never reaches the server.
              </p>
            </div>
          )}

          {/* Escrow payout status display */}
          {isEscrowActive && (
            <div className="rounded-md border border-blue-500/30 bg-blue-950/20 p-3 space-y-2 min-w-0 overflow-hidden">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-blue-300 truncate">
                  Escrow payout
                </p>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300">
                  {payout!.escrow_status}
                </span>
              </div>
              {payout!.escrow_coordinate && (
                <p className="text-xs text-muted-foreground truncate">
                  Agent: {payout!.escrow_coordinate}
                </p>
              )}
              <div className="flex gap-2">
                {payout!.escrow_status === "escrow_pending" && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleEscrowFunded}
                    disabled={sending}
                  >
                    {sending ? "Updating..." : "Mark as funded"}
                  </Button>
                )}
                {(payout!.escrow_status === "escrow_pending" ||
                  payout!.escrow_status === "escrow_funded") && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleEscrowReleased}
                    disabled={sending}
                  >
                    {sending ? "Updating..." : "Mark as released"}
                  </Button>
                )}
              </div>
            </div>
          )}

          <div className="rounded-md border border-slate-700 bg-slate-950/35 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-medium">Recipient claim QR</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Recipients scan, enter a Lightning Address, then you can send instantly from this wallet.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={generateClaimLinks}
                disabled={sending || !!payout}
              >
                {claims.length ? (
                  <RefreshCw className="mr-2 h-4 w-4" />
                ) : (
                  <QrCode className="mr-2 h-4 w-4" />
                )}
                {claims.length ? "Refresh claims" : "Create QR links"}
              </Button>
            </div>

            {claims.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-muted-foreground">
                  {claimedCount} of {claims.length} recipient{claims.length === 1 ? "" : "s"} ready.
                </p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {claims.map(claim => (
                    <div key={claim.id} className="rounded-md border border-slate-700 bg-slate-900/60 p-2">
                      <div className="flex gap-2">
                        <div className="shrink-0 rounded bg-white p-1">
                          <QRCode value={claim.claim_url} size={72} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-slate-100">{claim.name}</p>
                          <p className="font-mono text-xs text-muted-foreground">{claim.amount_sats} sats</p>
                          <p className={claim.lightning_address ? "text-xs text-green-400" : "text-xs text-amber-300"}>
                            {claim.lightning_address ? "Claimed" : "Waiting for scan"}
                          </p>
                          <a
                            href={claim.claim_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-blue-300 underline-offset-2 hover:text-blue-200 hover:underline"
                          >
                            Open link
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Split preview + address overrides */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Split preview and manual fallback</p>
            <div className="space-y-2">
              {team.members.map((member, i) => {
                const memberSats = base + (i < rem ? 1 : 0);
                const claim = claims.find(item => item.participant_id === member.id);
                return (
                  <div key={member.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{member.name}</span>
                      <span className="font-mono text-muted-foreground">{memberSats} sats</span>
                    </div>
                    <Input
                      type="text"
                      placeholder={claim?.lightning_address ?? "name@domain (optional)"}
                      value={addresses[member.id] ?? claim?.lightning_address ?? ""}
                      onChange={e =>
                        setAddresses(prev => ({ ...prev, [member.id]: e.target.value }))
                      }
                      className="h-7 text-xs"
                      // Re-enable for correction only when no wallet attempt exists.
                      disabled={!!payout && !hasFailedItems}
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {preflight.length > 0 && (
            <div className="rounded-md border border-slate-700 bg-slate-950/35 p-3">
              <p className="text-sm font-medium">Dry-run preflight</p>
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {preflight.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          )}

          {/* Results */}
          {payout && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Payout results</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(payout, null, 2)], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `squadsync-payout-${payout.id}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Export receipt
                </Button>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    payout.status === "complete"
                      ? "bg-green-100 text-green-700"
                      : payout.status === "partial"
                      ? "bg-amber-100 text-amber-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {payout.status}
                </span>
              </div>
              <div className="space-y-1.5">
                {payout.items.map(item => {
                  const member = team.members.find(m => m.id === item.participant_id);
                  return (
                    <div key={item.id} className="flex items-start gap-2 text-sm">
                      {item.status === "paid" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="font-medium">{member?.name ?? item.participant_id}</span>
                        {item.status === "paid" ? (
                          <span className="ml-2 text-muted-foreground">
                            {item.amount_sats} sats
                            {item.preimage && (
                              <span className="ml-1 font-mono text-xs">
                                · {item.preimage.slice(0, 12)}…
                              </span>
                            )}
                          </span>
                        ) : (
                          <span className="ml-2 text-red-600 text-xs truncate">
                            {item.error ?? (paymentAttempts[item.id] ? "Payment confirmation pending" : item.status)}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex-wrap gap-2">
          {!payout && payoutMode === "direct" && (
            <Button variant="outline" onClick={runDryCheck} disabled={sending}>
              Dry run
            </Button>
          )}
          {!payout && !isEscrowActive && (
            <Button onClick={handleSend} disabled={!canSend}>
              {payoutMode === "escrow" ? (
                <Shield className="mr-2 h-4 w-4" />
              ) : (
                <Zap className="mr-2 h-4 w-4" />
              )}
              {sending
                ? "Sending..."
                : payoutMode === "escrow"
                  ? "Create escrow payout"
                  : "Send payout"}
            </Button>
          )}
          {payout && hasFailedItems && payoutMode === "direct" && (
            <Button variant="outline" onClick={handleRetry} disabled={sending || !nwc}>
              {sending ? "Retrying…" : "Resume payout"}
            </Button>
          )}
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
