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

  it("uses the same-origin backend proxy when a session marker is provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await fetchAPI("/test", { token: "session" });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/backend/test");
    expect(options.headers["Authorization"]).toBeUndefined();
  });

  it("throws error with detail message on non-OK response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad request" }),
    });

    await expect(fetchAPI("/test")).rejects.toThrow("Bad request");
  });

  it("formats FastAPI validation errors", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: "Invalid address" }] }),
    });

    await expect(fetchAPI("/test")).rejects.toThrow("Invalid address");
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
