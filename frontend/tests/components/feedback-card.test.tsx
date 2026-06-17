import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchAPI } from "@/lib/api";
import { FeedbackCard } from "@/components/settings/feedback-card";

vi.mock("@/lib/api", () => ({ fetchAPI: vi.fn() }));
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { accessToken: "token" } }) }));
const toast = { success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({ toast: { success: (m: string) => toast.success(m), error: (m: string) => toast.error(m) } }));

beforeEach(() => vi.clearAllMocks());

describe("FeedbackCard", () => {
  it("submits feedback and shows a success toast", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockResolvedValue({ detail: "received" });
    render(<FeedbackCard />);
    fireEvent.change(screen.getByLabelText(/feedback/i), { target: { value: "love it" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(fetchAPI).toHaveBeenCalledWith(
      "/api/v1/feedback",
      expect.objectContaining({ method: "POST", body: { message: "love it" }, token: "token" }),
    ));
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("shows an error toast on failure", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("boom"));
    render(<FeedbackCard />);
    fireEvent.change(screen.getByLabelText(/feedback/i), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });

  it("disables send when the message is empty", () => {
    render(<FeedbackCard />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });
});
