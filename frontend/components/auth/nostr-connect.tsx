"use client";

import { useState, useEffect } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Zap, Key, RefreshCw, Eye, EyeOff, Copy, Check, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;
const SK_KEY = "squadsync:nostr_sk";

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexToBytes(hex: string): Uint8Array {
  return new Uint8Array(hex.match(/.{2}/g)!.map((b) => parseInt(b, 16)));
}

async function buildNip98Event(skHex: string) {
  const { finalizeEvent } = await import("nostr-tools");
  return finalizeEvent(
    {
      kind: 27235,
      created_at: Math.floor(Date.now() / 1000),
      tags: [
        ["u", `${API_URL}/auth/nostr`],
        ["method", "POST"],
      ],
      content: "",
    },
    hexToBytes(skHex)
  );
}

type View = "options" | "generated";

export function NostrConnect() {
  const router = useRouter();
  const [view, setView] = useState<View>("options");
  const [loading, setLoading] = useState(false);
  const [hasExtension, setHasExtension] = useState(false);
  const [storedNpub, setStoredNpub] = useState<string | null>(null);
  const [nsecInput, setNsecInput] = useState("");
  const [showNsec, setShowNsec] = useState(false);
  const [copied, setCopied] = useState<"npub" | "nsec" | null>(null);
  const [generated, setGenerated] = useState<{
    npub: string;
    nsec: string;
    skHex: string;
    pk: string;
  } | null>(null);

  useEffect(() => {
    setHasExtension(typeof window !== "undefined" && "nostr" in window);
    const skHex = localStorage.getItem(SK_KEY);
    if (skHex) {
      import("nostr-tools").then(({ getPublicKey }) =>
        import("nostr-tools/nip19").then(({ npubEncode }) =>
          setStoredNpub(npubEncode(getPublicKey(hexToBytes(skHex))))
        )
      );
    }
  }, []);

  const doSignIn = async (pubkey: string, signedEvent: object) => {
    setLoading(true);
    try {
      const result = await signIn("credentials", {
        pubkey,
        signedEvent: JSON.stringify(signedEvent),
        redirect: false,
      });
      if (result?.ok) {
        router.push("/dashboard");
        router.refresh();
      } else {
        toast.error("Authentication failed — signature rejected");
      }
    } finally {
      setLoading(false);
    }
  };

  const connectExtension = async () => {
    try {
      setLoading(true);
      const nostr = (window as Window & { nostr?: { getPublicKey(): Promise<string>; signEvent(e: object): Promise<object> } }).nostr!;
      const pubkey = await nostr.getPublicKey();
      const unsigned = {
        kind: 27235,
        created_at: Math.floor(Date.now() / 1000),
        tags: [
          ["u", `${API_URL}/auth/nostr`],
          ["method", "POST"],
        ],
        content: "",
      };
      const signedEvent = await nostr.signEvent(unsigned);
      await doSignIn(pubkey, signedEvent);
    } catch {
      toast.error("Extension connection failed");
      setLoading(false);
    }
  };

  const connectStoredKey = async () => {
    const skHex = localStorage.getItem(SK_KEY);
    if (!skHex) return;
    const { getPublicKey } = await import("nostr-tools");
    const pk = getPublicKey(hexToBytes(skHex));
    const event = await buildNip98Event(skHex);
    await doSignIn(pk, event);
  };

  const generateKey = async () => {
    const { generateSecretKey, getPublicKey } = await import("nostr-tools");
    const { nsecEncode, npubEncode } = await import("nostr-tools/nip19");
    const sk = generateSecretKey();
    const pk = getPublicKey(sk);
    const skHex = bytesToHex(sk);
    setGenerated({
      npub: npubEncode(pk),
      nsec: nsecEncode(sk),
      skHex,
      pk,
    });
    setView("generated");
  };

  const connectGenerated = async () => {
    if (!generated) return;
    localStorage.setItem(SK_KEY, generated.skHex);
    const event = await buildNip98Event(generated.skHex);
    await doSignIn(generated.pk, event);
  };

  const connectNsec = async () => {
    const raw = nsecInput.trim();
    if (!raw) return;
    try {
      const { decode } = await import("nostr-tools/nip19");
      const { getPublicKey } = await import("nostr-tools");
      const decoded = decode(raw);
      if (decoded.type !== "nsec") {
        toast.error("Must be an nsec key (starts with nsec1)");
        return;
      }
      const sk = decoded.data as Uint8Array;
      const pk = getPublicKey(sk);
      const skHex = bytesToHex(sk);
      localStorage.setItem(SK_KEY, skHex);
      const event = await buildNip98Event(skHex);
      await doSignIn(pk, event);
    } catch {
      toast.error("Invalid nsec key — check and try again");
    }
  };

  const copyText = async (text: string, which: "npub" | "nsec") => {
    await navigator.clipboard.writeText(text);
    setCopied(which);
    setTimeout(() => setCopied(null), 2000);
  };

  if (view === "generated" && generated) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Your new Nostr identity has been created. Save your secret key — it cannot be recovered.
        </p>

        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Public key (npub)
          </Label>
          <div className="flex gap-2">
            <Input
              readOnly
              value={generated.npub}
              className="font-mono text-xs"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() => copyText(generated.npub, "npub")}
            >
              {copied === "npub" ? (
                <Check className="h-3.5 w-3.5 text-green-600" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Secret key (nsec) — save this now
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                readOnly
                type={showNsec ? "text" : "password"}
                value={generated.nsec}
                className="font-mono text-xs pr-10"
              />
              <button
                type="button"
                onClick={() => setShowNsec(!showNsec)}
                className="absolute inset-y-0 right-2 flex items-center text-muted-foreground hover:text-foreground"
              >
                {showNsec ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
            <Button
              variant="outline"
              size="icon"
              onClick={() => copyText(generated.nsec, "nsec")}
            >
              {copied === "nsec" ? (
                <Check className="h-3.5 w-3.5 text-green-600" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
          <p className="text-xs text-amber-600 font-medium">
            ⚠ Anyone with this key can access your account. Never share it.
          </p>
        </div>

        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setView("options")}
          >
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            Back
          </Button>
          <Button
            className="flex-1"
            onClick={connectGenerated}
            disabled={loading}
          >
            {loading ? "Connecting…" : "I've saved my key — Sign In"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {hasExtension && (
        <Button
          className="w-full"
          variant="default"
          onClick={connectExtension}
          disabled={loading}
        >
          <Zap className="mr-2 h-4 w-4" />
          {loading ? "Connecting…" : "Connect with Nostr Extension"}
        </Button>
      )}

      {storedNpub && (
        <Button
          className="w-full font-mono text-xs"
          variant="secondary"
          onClick={connectStoredKey}
          disabled={loading}
        >
          <Key className="mr-2 h-4 w-4 shrink-0" />
          {loading ? "Connecting…" : `Resume as ${storedNpub.slice(0, 12)}…`}
        </Button>
      )}

      <Button
        className="w-full"
        variant="outline"
        onClick={generateKey}
        disabled={loading}
      >
        <RefreshCw className="mr-2 h-4 w-4" />
        Generate New Identity
      </Button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-muted-foreground">
            or paste existing key
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <Input
          id="nsec"
          type="password"
          placeholder="nsec1…"
          value={nsecInput}
          onChange={(e) => setNsecInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && connectNsec()}
          className="font-mono text-sm"
        />
        <Button
          className="w-full"
          variant="outline"
          onClick={connectNsec}
          disabled={loading || !nsecInput.trim()}
        >
          {loading ? "Verifying…" : "Connect with nsec key"}
        </Button>
      </div>
    </div>
  );
}
