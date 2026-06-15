import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { QuickGuideButton } from "@/components/onboarding/quick-guide-button";

beforeEach(() => localStorage.clear());

describe("QuickGuideButton", () => {
  it("renders a link to the guide", () => {
    render(<QuickGuideButton />);
    const link = screen.getByRole("link", { name: /quick guide/i });
    expect(link).toHaveAttribute("href", "/dashboard/settings/guide");
  });

  it("shows the highlight dot when not seen, hides it after click", async () => {
    render(<QuickGuideButton />);
    await waitFor(() => expect(screen.getByTestId("guide-dot")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("link", { name: /quick guide/i }));
    expect(localStorage.getItem("squadsync.guideSeen")).toBe("1");
    await waitFor(() => expect(screen.queryByTestId("guide-dot")).not.toBeInTheDocument());
  });

  it("does not show the dot when already seen", async () => {
    localStorage.setItem("squadsync.guideSeen", "1");
    render(<QuickGuideButton />);
    await waitFor(() => {}, { timeout: 50 });
    expect(screen.queryByTestId("guide-dot")).not.toBeInTheDocument();
  });
});
