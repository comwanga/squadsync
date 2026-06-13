import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConfigForm } from "@/components/configure/config-form";

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { accessToken: "token" } }) }));
vi.mock("swr", () => ({
  default: () => ({ data: { weight_experience: 0.5, weight_skill: 0.5, role_constraints: {} }, isLoading: false }),
  mutate: vi.fn(),
}));
vi.mock("@/components/ui/slider", () => ({
  Slider: ({ value }: { value: number[] }) => <div data-testid="slider">{value[0]}</div>,
}));
vi.mock("@/components/ui/select", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Select: ({ children }: { children: any }) => <div>{children}</div>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SelectTrigger: ({ children }: { children: any }) => <div>{children}</div>,
  SelectValue: () => <span />,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SelectContent: ({ children }: { children: any }) => <div>{children}</div>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SelectItem: ({ children, value }: { children: any; value: string }) => <div data-value={value}>{children}</div>,
}));

describe("ConfigForm", () => {
  it("renders weight sliders", () => {
    render(<ConfigForm eventId="event-123" />);
    expect(screen.getByText(/experience weight/i)).toBeInTheDocument();
    expect(screen.getByText(/skill weight/i)).toBeInTheDocument();
  });

  it("shows Add Constraint button", () => {
    render(<ConfigForm eventId="event-123" />);
    expect(screen.getByRole("button", { name: /add constraint/i })).toBeInTheDocument();
  });
});
