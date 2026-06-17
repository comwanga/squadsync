import { describe, it, expect } from "vitest";
import { GUIDE_STEPS } from "@/lib/guide-steps";

describe("GUIDE_STEPS", () => {
  it("has steps, each with the required fields", () => {
    expect(GUIDE_STEPS.length).toBe(10);
    for (const s of GUIDE_STEPS) {
      expect(s.id).toBeTruthy();
      expect(s.title).toBeTruthy();
      expect(s.caption).toBeTruthy();
      expect(s.image).toMatch(/^\/guide\/.+\.png$/);
    }
  });

  it("has unique ids", () => {
    const ids = GUIDE_STEPS.map(s => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
