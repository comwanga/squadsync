"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Zap, CheckCircle2, XCircle } from "lucide-react";
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
  retryPayout,
  type Payout,
  type Team,
} from "@/hooks/use-allocation";

interface PayoutModalProps {
  team: Team;
  allocationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PayoutModal({ team, allocationId, open, onOpenChange }: PayoutModalProps) {
  const { data: session } = useSession();
  const [totalSats, setTotalSats] = useState(2100);
  const [nwc, setNwc] = useState("");
  const [addresses, setAddresses] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [payout, setPayout] = useState<Payout | null>(null);

  const n = team.members.length;
  const base = n > 0 ? Math.floor(totalSats / n) : 0;
  const rem = n > 0 ? totalSats % n : 0;

  const handleOpenChange = (o: boolean) => {
    if (!o) {
      setNwc("");
    }
    onOpenChange(o);
  };

  const handleSend = async () => {
    if (!session?.accessToken) return;
    setSending(true);
    try {
      const nonEmptyAddresses: Record<string, string> = {};
      for (const [id, addr] of Object.entries(addresses)) {
        if (addr.trim()) nonEmptyAddresses[id] = addr.trim();
      }
      const result = await createPayout(session.accessToken, allocationId, {
        team_id: team.id,
        total_sats: totalSats,
        nwc,
        addresses: Object.keys(nonEmptyAddresses).length > 0 ? nonEmptyAddresses : undefined,
      });
      setPayout(result);
      toast.success("Payout sent!");
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 422) {
        toast.error(err.message);
      } else {
        toast.error(err instanceof Error ? err.message : "Payout failed");
      }
    } finally {
      setSending(false);
    }
  };

  const handleRetry = async () => {
    if (!session?.accessToken || !payout) return;
    setSending(true);
    try {
      const corrected: Record<string, string> = {};
      for (const [id, addr] of Object.entries(addresses)) {
        if (addr.trim()) corrected[id] = addr.trim();
      }
      const result = await retryPayout(session.accessToken, payout.id, nwc, corrected);
      setPayout(result);
      toast.success("Retry complete");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setSending(false);
    }
  };

  const canSend = !sending && !!nwc && totalSats >= n;
  const hasFailedItems = payout?.items.some(item => item.status === "failed");

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-amber-500" />
            Pay out {team.name}
          </DialogTitle>
          <DialogDescription>
            Send a Lightning payout to all members of this team via NWC.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
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

          {/* NWC input */}
          <div className="space-y-1.5">
            <Label htmlFor="nwc">NWC connection string</Label>
            <Input
              id="nwc"
              type="password"
              value={nwc}
              onChange={e => setNwc(e.target.value)}
              placeholder="nostr+walletconnect://..."
              disabled={!!payout}
            />
            <p className="text-xs text-muted-foreground">
              Paste an NWC string from Alby, Coinos, or Alby Hub. Used once to send — never stored.
            </p>
          </div>

          {/* Split preview + address overrides */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Split preview</p>
            <div className="space-y-2">
              {team.members.map((member, i) => {
                const memberSats = base + (i < rem ? 1 : 0);
                return (
                  <div key={member.id} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{member.name}</span>
                      <span className="font-mono text-muted-foreground">{memberSats} sats</span>
                    </div>
                    <Input
                      type="text"
                      placeholder="name@domain (optional)"
                      value={addresses[member.id] ?? ""}
                      onChange={e =>
                        setAddresses(prev => ({ ...prev, [member.id]: e.target.value }))
                      }
                      className="h-7 text-xs"
                      // Re-enable for correction when items failed and can be retried.
                      disabled={!!payout && !hasFailedItems}
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Results */}
          {payout && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Payout results</p>
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
                          <span className="ml-2 text-red-600 text-xs truncate">{item.error}</span>
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
          {!payout && (
            <Button onClick={handleSend} disabled={!canSend}>
              <Zap className="mr-2 h-4 w-4" />
              {sending ? "Sending…" : "Send payout"}
            </Button>
          )}
          {payout && hasFailedItems && (
            <Button variant="outline" onClick={handleRetry} disabled={sending || !nwc}>
              {sending ? "Retrying…" : "Retry failed"}
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
