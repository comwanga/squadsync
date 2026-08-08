import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { NostrIdentityProvider, useNostrIdentity } from "@/hooks/use-nostr-identity";

const storage: Record<string, string> = {};

const sessionStorageMock = {
  getItem: vi.fn((key: string) => storage[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    storage[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete storage[key];
  }),
};

vi.stubGlobal("sessionStorage", sessionStorageMock);

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <NostrIdentityProvider>{children}</NostrIdentityProvider>
);

describe("useNostrIdentity", () => {
  beforeEach(() => {
    Object.keys(storage).forEach((k) => delete storage[k]);
    vi.clearAllMocks();
  });

  it("starts with null capability", () => {
    const { result } = renderHook(() => useNostrIdentity(), { wrapper });
    expect(result.current.capability).toBeNull();
  });

  it("sets and retrieves nsec capability", () => {
    const { result } = renderHook(() => useNostrIdentity(), { wrapper });

    act(() => {
      result.current.setCapability({
        type: "nsec",
        skHex: "01".repeat(32),
        pk: "pubkey123",
      });
    });

    expect(result.current.capability).toEqual({
      type: "nsec",
      skHex: "01".repeat(32),
      pk: "pubkey123",
    });
  });

  it("persists nsec to sessionStorage", () => {
    const { result } = renderHook(() => useNostrIdentity(), { wrapper });

    act(() => {
      result.current.setCapability({
        type: "nsec",
        skHex: "ab".repeat(32),
        pk: "pk1",
      });
    });

    expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
      "squadsync-nostr-identity",
      JSON.stringify({ type: "nsec", skHex: "ab".repeat(32), pk: "pk1" }),
    );
  });

  it("clears capability", () => {
    const { result } = renderHook(() => useNostrIdentity(), { wrapper });

    act(() => {
      result.current.setCapability({
        type: "nsec",
        skHex: "01".repeat(32),
        pk: "pk1",
      });
    });

    act(() => {
      result.current.clearCapability();
    });

    expect(result.current.capability).toBeNull();
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(
      "squadsync-nostr-identity",
    );
  });

  it("signEvent throws when no capability", async () => {
    const { result } = renderHook(() => useNostrIdentity(), { wrapper });
    await expect(
      result.current.signEvent({
        kind: 30361,
        created_at: 1,
        tags: [],
        content: "{}",
      }),
    ).rejects.toThrow("No signing capability available");
  });

  it("throws when used outside provider", () => {
    expect(() => renderHook(() => useNostrIdentity())).toThrow(
      "useNostrIdentity must be used within NostrIdentityProvider",
    );
  });
});
