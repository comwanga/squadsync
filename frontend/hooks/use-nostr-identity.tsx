"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { Event as NostrEvent, EventTemplate } from "nostr-tools";

type SigningCapability =
  | { type: "nsec"; skHex: string; pk: string }
  | { type: "extension"; pk: string }
  | null;

const SESSION_KEY = "squadsync-nostr-identity";

interface NostrIdentity {
  capability: SigningCapability;
  setCapability: (c: SigningCapability) => void;
  signEvent: (template: EventTemplate) => Promise<NostrEvent>;
  clearCapability: () => void;
}

const NostrIdentityContext = createContext<NostrIdentity | null>(null);

function loadFromSession(): SigningCapability {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      parsed.type === "nsec" &&
      typeof parsed.skHex === "string" &&
      typeof parsed.pk === "string"
    ) {
      return { type: "nsec", skHex: parsed.skHex, pk: parsed.pk };
    }
    return null;
  } catch {
    return null;
  }
}

function persistToSession(cap: SigningCapability) {
  if (typeof window === "undefined") return;
  try {
    if (cap && cap.type === "nsec") {
      sessionStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ type: "nsec", skHex: cap.skHex, pk: cap.pk }),
      );
    } else {
      sessionStorage.removeItem(SESSION_KEY);
    }
  } catch {
    // sessionStorage unavailable (private browsing, etc.)
  }
}

function hexToBytes(hex: string): Uint8Array {
  return new Uint8Array(hex.match(/.{2}/g)?.map((b) => parseInt(b, 16)) ?? []);
}

async function signWithNsec(
  skHex: string,
  template: EventTemplate,
): Promise<NostrEvent> {
  const { finalizeEvent } = await import("nostr-tools");
  return finalizeEvent(template, hexToBytes(skHex));
}

async function signWithExtension(
  template: EventTemplate,
): Promise<NostrEvent> {
  const nostr = (window as Window & { nostr?: { signEvent(e: object): Promise<object> } }).nostr;
  if (!nostr) throw new Error("Nostr extension no longer available");
  const signed = await nostr.signEvent(template);
  return signed as NostrEvent;
}

export function NostrIdentityProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [capability, setCapabilityState] =
    useState<SigningCapability>(null);

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setCapabilityState(loadFromSession());
    setMounted(true);
  }, []);

  const setCapability = useCallback((c: SigningCapability) => {
    persistToSession(c);
    setCapabilityState(c);
  }, []);

  const clearCapability = useCallback(() => {
    persistToSession(null);
    setCapabilityState(null);
  }, []);

  const signEvent = useCallback(
    async (template: EventTemplate): Promise<NostrEvent> => {
      if (!capability) throw new Error("No signing capability available");
      if (capability.type === "nsec") {
        return signWithNsec(capability.skHex, template);
      }
      return signWithExtension(template);
    },
    [capability],
  );

  const value = mounted
    ? { capability, setCapability, signEvent, clearCapability }
    : { capability: null, setCapability, signEvent, clearCapability };

  return (
    <NostrIdentityContext.Provider value={value}>
      {children}
    </NostrIdentityContext.Provider>
  );
}

export function useNostrIdentity(): NostrIdentity {
  const ctx = useContext(NostrIdentityContext);
  if (!ctx) throw new Error("useNostrIdentity must be used within NostrIdentityProvider");
  return ctx;
}
