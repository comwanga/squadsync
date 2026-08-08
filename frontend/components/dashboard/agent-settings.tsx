"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Shield, Globe, Zap, Loader2, Info,
  RefreshCw, Plus, ChevronDown, ChevronUp, Calendar,
  CircleDot, Copy, Check,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { useNostrIdentity } from "@/hooks/use-nostr-identity";
import { EscrowType, buildEscrowEventTemplate } from "@/lib/pip01";
import { fetchAPI } from "@/lib/api";

interface PublishedAgent {
  coordinate: string;
  pubkey?: string;
  escrow_type: string;
  networks: string[];
  funding_rules: { required_confirmation: string };
  release_rules: { release_trigger: string; refund_trigger: string };
  dispute_rules: { policy: string };
  reference_format: string;
  content?: Record<string, unknown> | null;
}

function agentName(agent: PublishedAgent): string {
  const coord = agent.coordinate || "";
  const parts = coord.split(":");
  const ident = parts[2];
  if (ident && ident !== "escrow" && ident.length <= 30) return ident;
  if (ident && ident.length > 30) return ident.slice(0, 28) + "\u2026";
  const pubkey = parts[1] || "";
  return pubkey.slice(0, 12) + "\u2026" + pubkey.slice(-4) || "Unknown agent";
}

function agentPubkey(agent: PublishedAgent): string {
  const parts = (agent.coordinate || "").split(":");
  return parts[1] || agent.pubkey || "";
}

function networkBadgeColor(network: string): string {
  const lower = network.toLowerCase();
  if (lower === "lightning") return "bg-amber-600/20 text-amber-300 border-amber-600/30";
  if (lower === "bitcoin") return "bg-orange-600/20 text-orange-300 border-orange-600/30";
  if (lower === "spark") return "bg-purple-600/20 text-purple-300 border-purple-600/30";
  return "bg-slate-600/20 text-slate-300 border-slate-600/30";
}

function typeBadgeColor(type: string): string {
  if (type === "custodial_escrow") return "bg-blue-600/20 text-blue-300 border-blue-600/30";
  if (type === "lightning_hold_invoice") return "bg-amber-600/20 text-amber-300 border-amber-600/30";
  return "bg-slate-600/20 text-slate-300 border-slate-600/30";
}

export function AgentSettings() {
  const router = useRouter();
  const { data: session } = useSession();
  const { capability, signEvent } = useNostrIdentity();

  const [activeTab, setActiveTab] = useState<"available" | "mine">("available");
  const [agentList, setAgentList] = useState<PublishedAgent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<PublishedAgent | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expandedTech, setExpandedTech] = useState(false);
  const loadedRef = useRef(false);

  // --- Registration form state ---
  const [identifier, setIdentifier] = useState("");
  const [releaseTrigger, setReleaseTrigger] = useState("SquadSync allocation published");
  const [refundTrigger, setRefundTrigger] = useState("48 hours after event end or organizer cancel");
  const [disputePolicy, setDisputePolicy] = useState("mutual agreement between parties");
  const [invoiceCurrency, setInvoiceCurrency] = useState("BTC");
  const [invoiceExpiryRule, setInvoiceExpiryRule] = useState("24h");
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    fetchAPI<{ agents: PublishedAgent[] }>("/api/v1/escrow/agents")
      .then((res) => setAgentList(res.agents))
      .catch(() => { /* non-critical */ });
  }, []);

  const refreshAgents = async () => {
    try {
      const res = await fetchAPI<{ agents: PublishedAgent[] }>("/api/v1/escrow/agents");
      setAgentList(res.agents);
    } catch { /* non-critical */ }
  };

  const myAgents = capability?.pk
    ? agentList.filter((a) => a.coordinate.includes(capability.pk))
    : [];
  const availableAgents = agentList.filter(
    (a) => !capability?.pk || !a.coordinate.includes(capability.pk),
  );
  const displayAgents = activeTab === "mine" ? myAgents : availableAgents;
  const hasKey = capability && capability.type !== "extension";

  const openDetail = (agent: PublishedAgent) => {
    setSelectedAgent(agent);
    setExpandedTech(false);
    setDetailOpen(true);
  };

  const copyCoordinate = async (coord: string) => {
    await navigator.clipboard.writeText(coord);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
      await fetchAPI<{ coordinate: string; status: string }>(
        "/api/v1/escrow/publish",
        { method: "POST", body: { event }, token: session?.accessToken },
      );
      toast.success("Escrow agent published to Nostr");
      setRegisterOpen(false);
      setIdentifier("");
      refreshAgents();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to publish agent");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Escrow Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Discover escrow services on the Nostr network, or register your own.
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={refreshAgents} variant="outline" size="sm" className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button
            onClick={() => setRegisterOpen(true)}
            size="sm"
            className="gap-1.5"
            disabled={!hasKey}
          >
            <Plus className="h-3.5 w-3.5" />
            Register agent
          </Button>
        </div>
      </div>

      {/* No-key warning */}
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
                    ? "Browser extension users can browse agents but need a local key to register. Log in with a generated or pasted key."
                    : "Log in with a Nostr key to register as an escrow agent."}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex rounded-lg border border-slate-700 bg-slate-950/35 p-1">
        <button
          type="button"
          onClick={() => setActiveTab("available")}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            activeTab === "available"
              ? "bg-slate-800 text-slate-100"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Globe className="inline h-3.5 w-3.5 mr-1.5" />
          Available
          {availableAgents.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({availableAgents.length})</span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("mine")}
          className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            activeTab === "mine"
              ? "bg-slate-800 text-slate-100"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Shield className="inline h-3.5 w-3.5 mr-1.5" />
          My agents
          {myAgents.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({myAgents.length})</span>
          )}
        </button>
      </div>

      {/* Agent grid */}
      {displayAgents.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Shield className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium text-muted-foreground">
              {activeTab === "mine"
                ? "You haven't registered any agents yet."
                : "No escrow agents discovered on Nostr relays."}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {activeTab === "mine"
                ? "Click Register agent to publish your escrow service."
                : "Try refreshing, or register your own agent to appear here."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {displayAgents.map((agent) => (
            <button
              key={agent.coordinate}
              type="button"
              onClick={() => openDetail(agent)}
              className="text-left rounded-lg border border-slate-700 bg-slate-900/60 p-4 transition-colors hover:border-slate-500 hover:bg-slate-900/80 min-w-0 overflow-hidden"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-100 truncate">
                    {agentName(agent)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                    {agent.release_rules.release_trigger}
                  </p>
                </div>
                <CircleDot className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
              </div>

              <div className="flex flex-wrap gap-1.5 mt-3">
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${typeBadgeColor(agent.escrow_type)}`}
                >
                  {agent.escrow_type.replace(/_/g, " ")}
                </Badge>
                {agent.networks.map((net) => (
                  <Badge
                    key={net}
                    variant="outline"
                    className={`text-[10px] px-1.5 py-0 ${networkBadgeColor(net)}`}
                  >
                    {net}
                  </Badge>
                ))}
              </div>

              <p className="text-[11px] text-muted-foreground mt-2.5 truncate">
                Refund: {agent.release_rules.refund_trigger}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* Agent detail dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
          {selectedAgent && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-lg">
                  <Shield className="h-5 w-5 text-blue-400" />
                  {agentName(selectedAgent)}
                </DialogTitle>
                <DialogDescription>
                  Escrow agent details and capabilities
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Status */}
                <div className="flex items-center gap-2 text-sm">
                  <CircleDot className="h-4 w-4 text-green-500" />
                  <span className="font-medium text-green-400">Online</span>
                  <span className="text-muted-foreground">— seen on relays</span>
                </div>

                {/* Type + Networks */}
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="outline" className={typeBadgeColor(selectedAgent.escrow_type)}>
                      {selectedAgent.escrow_type.replace(/_/g, " ")}
                    </Badge>
                    {selectedAgent.networks.map((net) => (
                      <Badge key={net} variant="outline" className={networkBadgeColor(net)}>
                        {net}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Rules */}
                <div className="rounded-md border border-slate-700 bg-slate-950/35 p-3 space-y-2.5">
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                      Release
                    </p>
                    <p className="text-sm text-slate-200 mt-0.5">
                      {selectedAgent.release_rules.release_trigger}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                      Refund
                    </p>
                    <p className="text-sm text-slate-200 mt-0.5">
                      {selectedAgent.release_rules.refund_trigger}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                      Dispute
                    </p>
                    <p className="text-sm text-slate-200 mt-0.5">
                      {selectedAgent.dispute_rules.policy}
                    </p>
                  </div>
                  {selectedAgent.funding_rules.required_confirmation && (
                    <div>
                      <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                        Funding confirmation
                      </p>
                      <p className="text-sm text-slate-200 mt-0.5">
                        {selectedAgent.funding_rules.required_confirmation}
                      </p>
                    </div>
                  )}
                </div>

                {/* Technical details (collapsible) */}
                <div>
                  <button
                    type="button"
                    onClick={() => setExpandedTech(!expandedTech)}
                    className="flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-300 transition-colors"
                  >
                    {expandedTech ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                    Technical details
                  </button>
                  {expandedTech && (
                    <div className="mt-2 rounded-md border border-slate-700 bg-slate-950/35 p-3 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">
                            Coordinate
                          </p>
                          <p className="text-xs font-mono text-slate-300 break-all mt-0.5">
                            {selectedAgent.coordinate}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyCoordinate(selectedAgent.coordinate);
                          }}
                        >
                          {copied ? (
                            <Check className="h-3 w-3 text-green-400" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                      {agentPubkey(selectedAgent) && (
                        <div>
                          <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">
                            Pubkey
                          </p>
                          <p className="text-xs font-mono text-slate-300 break-all mt-0.5">
                            {agentPubkey(selectedAgent)}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1 gap-1.5"
                  onClick={() => {
                    setDetailOpen(false);
                    router.push(`/dashboard/escrows/create?agent=${encodeURIComponent(selectedAgent.coordinate)}`);
                  }}
                >
                  <Calendar className="h-4 w-4" />
                  Use this agent
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Register agent dialog */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Shield className="h-5 w-5" />
              Register escrow agent
            </DialogTitle>
            <DialogDescription>
              Publish your escrow service to the Pontmore network so other
              organizers can discover and use it.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="agent-identifier">Agent name</Label>
              <Input
                id="agent-identifier"
                placeholder="e.g. Squad Agent"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A short name for your escrow service. If empty, defaults to
                &ldquo;escrow&rdquo;.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="release-trigger">Release trigger</Label>
              <Input
                id="release-trigger"
                value={releaseTrigger}
                onChange={(e) => setReleaseTrigger(e.target.value)}
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
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="invoice-currency">Invoice currency</Label>
                <Input
                  id="invoice-currency"
                  value={invoiceCurrency}
                  onChange={(e) => setInvoiceCurrency(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invoice-expiry">Invoice expiry</Label>
                <Input
                  id="invoice-expiry"
                  value={invoiceExpiryRule}
                  onChange={(e) => setInvoiceExpiryRule(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setRegisterOpen(false)}
            >
              Cancel
            </Button>
            <Button
              className="flex-1 gap-1.5"
              onClick={handlePublish}
              disabled={!hasKey || publishing}
            >
              {publishing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              Publish agent
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
