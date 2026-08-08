"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Shield, Globe, Zap, Loader2, CheckCircle, Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNostrIdentity } from "@/hooks/use-nostr-identity";
import { EscrowType, buildEscrowEventTemplate, escrowCoordinate } from "@/lib/pip01";
import { fetchAPI } from "@/lib/api";

interface PublishedAgent {
  coordinate: string;
  escrow_type: string;
  networks: string[];
  funding_rules: { required_confirmation: string };
  release_rules: { release_trigger: string; refund_trigger: string };
  dispute_rules: { policy: string };
  reference_format: string;
}

export function AgentSettings() {
  const { data: session } = useSession();
  const { capability, signEvent } = useNostrIdentity();

  const [identifier, setIdentifier] = useState("");
  const [releaseTrigger, setReleaseTrigger] = useState(
    "SquadSync allocation published",
  );
  const [refundTrigger, setRefundTrigger] = useState(
    "48 hours after event end or organizer cancel",
  );
  const [disputePolicy, setDisputePolicy] = useState("mutual agreement between parties");
  const [invoiceCurrency, setInvoiceCurrency] = useState("BTC");
  const [invoiceExpiryRule, setInvoiceExpiryRule] = useState("24h");
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState<PublishedAgent | null>(null);
  const [agentList, setAgentList] = useState<PublishedAgent[]>([]);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    fetchAPI<{ agents: PublishedAgent[] }>("/api/v1/escrow/agents")
      .then((res) => {
        setAgentList(res.agents);
        const myCoord = capability?.pk
          ? escrowCoordinate(capability.pk, identifier || undefined)
          : null;
        if (myCoord) {
          const existing = res.agents.find((a) => a.coordinate === myCoord);
          if (existing) setPublished(existing);
        }
      })
      .catch(() => { /* agent list is non-critical */ });
  }, []);

  const refreshAgents = async () => {
    try {
      const res = await fetchAPI<{ agents: PublishedAgent[] }>(
        "/api/v1/escrow/agents",
      );
      setAgentList(res.agents);
      const myCoord = capability?.pk
        ? escrowCoordinate(capability.pk, identifier || undefined)
        : null;
      if (myCoord) {
        const existing = res.agents.find((a) => a.coordinate === myCoord);
        if (existing) setPublished(existing);
      }
    } catch {
      // silent: agent list is non-critical
    }
  };

  const handlePublish = async () => {
    if (!capability) {
      toast.error("Sign in with a Nostr key to publish an agent");
      return;
    }

    const pk = capability.pk;
    setPublishing(true);
    try {
      const template = buildEscrowEventTemplate({
        pubkey: pk,
        identifier: identifier || undefined,
        escrowType: EscrowType.CustodialEscrow,
        networks: ["lightning"],
        releaseTrigger,
        refundTrigger,
        disputePolicy,
        invoiceNetwork: "lightning",
        invoiceCurrency,
        invoiceExpiryRule,
        custodyAuthority: pk,
        releaseAuthority: "event organizer",
        refundAuthority: pk,
        referenceFormat: "squadsync-allocation-id",
        payoutNetwork: "lightning",
      });

      const event = await signEvent(template);

      const res = await fetchAPI<{ coordinate: string; status: string }>(
        "/api/v1/escrow/publish",
        {
          method: "POST",
          body: { event },
          token: session?.accessToken,
        },
      );

      const agent: PublishedAgent = {
        coordinate: res.coordinate,
        escrow_type: "custodial_escrow",
        networks: ["lightning"],
        funding_rules: {
          required_confirmation: "deposit bolt11 paid",
        },
        release_rules: {
          release_trigger: releaseTrigger,
          refund_trigger: refundTrigger,
        },
        dispute_rules: { policy: disputePolicy },
        reference_format: "squadsync-allocation-id",
      };

      setPublished(agent);
      toast.success("Escrow agent published to Nostr");
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Failed to publish agent",
      );
    } finally {
      setPublishing(false);
    }
  };

  const hasKey = capability && capability.type !== "extension";

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Escrow Agent</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Register as a Pontmore escrow agent. Other event organizers can then
          discover you on Nostr and use your escrow service for prize payouts.
        </p>
      </div>

      {!hasKey && (
        <Card className="border-amber-400/40 bg-amber-50/30 dark:bg-amber-950/20">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                  Nostr key required
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                  {capability?.type === "extension"
                    ? "Browser extension keys can sign, but the key is not available for agent management. Log in with a local key to register as an agent."
                    : "Log in with a Nostr key (not a browser extension) to register as an escrow agent. This key will sign your agent descriptor."}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {published && (
        <Card className="border-green-400/40 bg-green-50/30 dark:bg-green-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle className="h-4 w-4 text-green-600" />
              Agent published
            </CardTitle>
            <CardDescription>
              Your escrow agent is live on the Nostr network. Other organizers
              can discover you when setting up prize payouts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm min-w-0">
              <p className="truncate">
                <span className="font-medium">Coordinate:</span>{" "}
                <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded break-all">
                  {published.coordinate}
                </code>
              </p>
              <p>
                <span className="font-medium">Type:</span>{" "}
                {published.escrow_type}
              </p>
              <p>
                <span className="font-medium">Release:</span>{" "}
                {published.release_rules.release_trigger}
              </p>
              <p>
                <span className="font-medium">Refund:</span>{" "}
                {published.release_rules.refund_trigger}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Agent configuration
          </CardTitle>
          <CardDescription>
            Set up how your escrow service works. Publish to make it discoverable,
            or republish to update.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="agent-identifier">Agent identifier</Label>
            <Input
              id="agent-identifier"
              placeholder="e.g. my-lightning-escrow"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              disabled={!hasKey}
            />
            <p className="text-xs text-muted-foreground">
              A short slug. If left empty, defaults to &ldquo;escrow&rdquo;.
              Your coordinate will be{" "}
              <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">
                30361:{capability?.pk?.slice(0, 8) ?? "pubkey"}
                :{identifier || "escrow"}
              </code>
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="release-trigger">Release trigger</Label>
            <Input
              id="release-trigger"
              value={releaseTrigger}
              onChange={(e) => setReleaseTrigger(e.target.value)}
              disabled={!hasKey}
            />
            <p className="text-xs text-muted-foreground">
              When do funds get released to recipients?
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="refund-trigger">Refund trigger</Label>
            <Input
              id="refund-trigger"
              value={refundTrigger}
              onChange={(e) => setRefundTrigger(e.target.value)}
              disabled={!hasKey}
            />
            <p className="text-xs text-muted-foreground">
              When do deposited funds get refunded?
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="dispute-policy">Dispute policy</Label>
            <Input
              id="dispute-policy"
              value={disputePolicy}
              onChange={(e) => setDisputePolicy(e.target.value)}
              disabled={!hasKey}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="invoice-currency">Invoice currency</Label>
              <Input
                id="invoice-currency"
                value={invoiceCurrency}
                onChange={(e) => setInvoiceCurrency(e.target.value)}
                disabled={!hasKey}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="invoice-expiry">Invoice expiry</Label>
              <Input
                id="invoice-expiry"
                value={invoiceExpiryRule}
                onChange={(e) => setInvoiceExpiryRule(e.target.value)}
                disabled={!hasKey}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button onClick={refreshAgents} variant="outline" className="gap-2">
          <Globe className="h-4 w-4" />
          Refresh agents
        </Button>
        <Button
          onClick={handlePublish}
          disabled={!hasKey || publishing || !identifier.trim()}
          className="gap-2"
        >
          {publishing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {published ? "Republish agent" : "Publish as agent"}
        </Button>
      </div>

      {agentList.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Discovered agents ({agentList.length})
            </CardTitle>
            <CardDescription>
              Agents found on Nostr relays and published locally.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {agentList.map((agent) => (
                <div
                  key={agent.coordinate}
                  className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 p-3 min-w-0 overflow-hidden"
                >
                  <p className="text-sm font-medium truncate">
                    {agent.coordinate}
                    {agent.coordinate === published?.coordinate && (
                      <span className="ml-2 text-xs text-green-600">(you)</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">
                    {agent.escrow_type} &middot; {agent.networks.join(", ")}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    Release: {agent.release_rules.release_trigger} &middot;{" "}
                    Refund: {agent.release_rules.refund_trigger}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
