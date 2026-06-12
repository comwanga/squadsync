import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mock
import { fetchAPI } from "@/lib/api";

describe("fetchAPI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends JSON request with base URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: "ok" }),
    });

    const result = await fetchAPI("/test");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/test"),
      expect.any(Object)
    );
    expect(result).toEqual({ data: "ok" });
  });

  it("includes Authorization header when token provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await fetchAPI("/test", { token: "my-jwt" });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe("Bearer my-jwt");
  });

  it("throws error with detail message on non-OK response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad request" }),
    });

    await expect(fetchAPI("/test")).rejects.toThrow("Bad request");
  });

  it("sends POST body as JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await fetchAPI("/test", { method: "POST", body: { name: "Alice" } });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.body).toBe(JSON.stringify({ name: "Alice" }));
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
});
