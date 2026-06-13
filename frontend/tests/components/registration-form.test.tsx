import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RegistrationForm } from "@/components/registration/registration-form";

vi.mock("@/lib/api", () => ({
  fetchAPI: vi.fn().mockResolvedValue({ name: "Alice", id: "p-1" }),
}));

const mockEvent = {
  id: "e-1",
  title: "Hackathon 2026",
  status: "active",
  description: "Build stuff",
};

describe("RegistrationForm", () => {
  it("renders all required fields", () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByText(/skill level/i)).toBeInTheDocument();
    expect(screen.getByText(/preferred role/i)).toBeInTheDocument();
  });

  it("shows validation error when name is empty", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it("shows confirmation after successful submit", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    await waitFor(() => {
      expect(screen.getByText(/you're registered/i)).toBeInTheDocument();
    });
  });
});
