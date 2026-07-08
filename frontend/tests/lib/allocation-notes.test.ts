import { describe, it, expect } from "vitest";
import { normalizationNote } from "@/lib/allocation-notes";

describe("normalizationNote", () => {
  it("reports optional helper count when present", () => {
    expect(normalizationNote(2, 0)).toMatch(/2 free-text "Other" responses categorized with the optional helper/i);
  });
  it("reports fallback when no AI", () => {
    expect(normalizationNote(0, 3)).toMatch(/categorized automatically/i);
  });
  it("returns null when nothing was normalized", () => {
    expect(normalizationNote(0, 0)).toBeNull();
  });
});
