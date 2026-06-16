import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SourceBadge } from "@/components/attendees/source-badge";

describe("SourceBadge", () => {
  it("labels each source", () => {
    const cases: [string, string][] = [
      ["ai", "AI"], ["fallback", "Auto"], ["manual", "Manual"], ["preset", "preset"],
    ];
    for (const [source, label] of cases) {
      const { unmount } = render(<SourceBadge source={source} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });
});
