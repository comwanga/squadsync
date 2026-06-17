import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Breadcrumb } from "@/components/layout/breadcrumb";

describe("Breadcrumb", () => {
  it("renders all segment labels", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "My Event", href: "/dashboard/events/1" },
      { label: "Attendees" },
    ]} />);
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("My Event")).toBeInTheDocument();
    expect(screen.getByText("Attendees")).toBeInTheDocument();
  });

  it("renders parent items (with href, not last) as links", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "Attendees" },
    ]} />);
    expect(screen.getByRole("link", { name: "Events" })).toHaveAttribute("href", "/dashboard/events");
  });

  it("renders the last item as the current page, not a link", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "Attendees" },
    ]} />);
    expect(screen.queryByRole("link", { name: "Attendees" })).toBeNull();
    expect(screen.getByText("Attendees")).toHaveAttribute("aria-current", "page");
  });

  it("never links the last item even if it has an href", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "My Event", href: "/dashboard/events/1" },
    ]} />);
    expect(screen.queryByRole("link", { name: "My Event" })).toBeNull();
    expect(screen.getByText("My Event")).toHaveAttribute("aria-current", "page");
  });

  it("exposes a labelled breadcrumb nav", () => {
    render(<Breadcrumb items={[{ label: "Events", href: "/dashboard/events" }, { label: "X" }]} />);
    expect(screen.getByRole("navigation", { name: /breadcrumb/i })).toBeInTheDocument();
  });
});
