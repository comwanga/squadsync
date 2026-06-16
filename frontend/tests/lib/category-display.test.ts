import { describe, it, expect } from "vitest";
import { isKnownStrength, categoryPlaceholder } from "@/lib/category-display";

describe("isKnownStrength", () => {
  it("is true for a concrete strength value", () => {
    expect(isKnownStrength("domain_expert")).toBe(true);
  });
  it("is false for a fallback slug / unknown / empty", () => {
    expect(isKnownStrength("agronomist")).toBe(false);
    expect(isKnownStrength("other")).toBe(false);
    expect(isKnownStrength(undefined)).toBe(false);
  });
});

describe("categoryPlaceholder", () => {
  it("prefers the original free text", () => {
    expect(categoryPlaceholder({ normalized_strength: "agronomist", strength_other: "Agronomist" }))
      .toBe("Agronomist");
  });
  it("falls back to a de-slugged normalized value", () => {
    expect(categoryPlaceholder({ normalized_strength: "agronomist" })).toBe("agronomist");
    expect(categoryPlaceholder({ normalized_strength: "data_science" })).toBe("data science");
  });
  it("uses a generic prompt when nothing is set", () => {
    expect(categoryPlaceholder({})).toBe("Set category");
  });
});
