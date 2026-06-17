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
    expect(screen.getByText(/primary strength/i)).toBeInTheDocument();
    expect(screen.getByText(/^experience$/i)).toBeInTheDocument();
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

  it("renders the experience segmented control with three options", () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    expect(screen.getByRole("radio", { name: /beginner/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /advanced/i })).toBeInTheDocument();
  });

  it("renders the optional npub field", () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    expect(screen.getByLabelText(/npub/i)).toBeInTheDocument();
  });

  it("includes npub in the submit body when provided", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.change(screen.getByLabelText(/npub/i), { target: { value: "npub1abc" } });
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    const { fetchAPI } = await import("@/lib/api");
    await waitFor(() => expect(fetchAPI).toHaveBeenCalledWith(
      "/api/v1/events/abc123/register",
      expect.objectContaining({ method: "POST", body: expect.objectContaining({ npub: "npub1abc" }) }),
    ));
  });
});
