import { describe, it, expect } from "vitest";
import { formatEventDate } from "@/lib/format-date";

describe("formatEventDate", () => {
  it("returns 'No date' when missing", () => {
    expect(formatEventDate(undefined)).toBe("No date");
    expect(formatEventDate("")).toBe("No date");
  });
  it("formats a datetime to a readable string containing the year", () => {
    expect(formatEventDate("2026-07-15T14:00:00")).toMatch(/2026/);
  });
});
