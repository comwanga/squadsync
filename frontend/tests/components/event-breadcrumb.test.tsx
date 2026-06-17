import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EventBreadcrumb, EventBreadcrumbAuto } from "@/components/layout/event-breadcrumb";
import { useEvent } from "@/hooks/use-events";

vi.mock("@/hooks/use-events", () => ({ useEvent: vi.fn() }));
const mockUseEvent = useEvent as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("EventBreadcrumb (pure)", () => {
  it("links the title and marks the current leaf", () => {
    render(<EventBreadcrumb eventId="e1" title="Hackathon 2026" current="Attendees" />);
    expect(screen.getByRole("link", { name: "Hackathon 2026" })).toHaveAttribute("href", "/dashboard/events/e1");
    expect(screen.getByText("Attendees")).toHaveAttribute("aria-current", "page");
  });

  it("uses the title as the leaf when no current is given", () => {
    render(<EventBreadcrumb eventId="e1" title="Hackathon 2026" />);
    expect(screen.queryByRole("link", { name: "Hackathon 2026" })).toBeNull();
    expect(screen.getByText("Hackathon 2026")).toHaveAttribute("aria-current", "page");
  });

  it("shows a skeleton when title is undefined", () => {
    render(<EventBreadcrumb eventId="e1" current="Attendees" />);
    expect(screen.getByTestId("breadcrumb-title-skeleton")).toBeInTheDocument();
    expect(screen.getByText("Attendees")).toBeInTheDocument();
  });
});

describe("EventBreadcrumbAuto (self-resolving)", () => {
  it("resolves the title and marks the current leaf", () => {
    mockUseEvent.mockReturnValue({ event: { id: "e1", title: "Hackathon 2026" }, isLoading: false });
    render(<EventBreadcrumbAuto eventId="e1" current="Configure" />);
    expect(screen.getByRole("link", { name: "Hackathon 2026" })).toHaveAttribute("href", "/dashboard/events/e1");
    expect(screen.getByText("Configure")).toHaveAttribute("aria-current", "page");
  });

  it("shows a skeleton while loading", () => {
    mockUseEvent.mockReturnValue({ event: undefined, isLoading: true });
    render(<EventBreadcrumbAuto eventId="e1" current="Allocation" />);
    expect(screen.getByTestId("breadcrumb-title-skeleton")).toBeInTheDocument();
    expect(screen.getByText("Allocation")).toBeInTheDocument();
  });

  it("falls back to 'Event' when loaded with no event", () => {
    mockUseEvent.mockReturnValue({ event: undefined, isLoading: false });
    render(<EventBreadcrumbAuto eventId="e1" current="Configure" />);
    expect(screen.getByText("Event")).toBeInTheDocument();
  });
});
