import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchAPI } from "@/lib/api";
import { FindMyTeam } from "@/components/results/find-my-team";

vi.mock("@/lib/api", () => ({ fetchAPI: vi.fn() }));

beforeEach(() => vi.clearAllMocks());

describe("FindMyTeam", () => {
  it("shows the matched team and teammates on success", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "t1", name: "Team 01", members: [{ id: "a", name: "Alice" }, { id: "b", name: "Bob" }],
    });
    render(<FindMyTeam allocationId="alloc-1" />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /find my team/i }));
    await waitFor(() => expect(screen.getByText(/Team 01/)).toBeInTheDocument());
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
  });

  it("shows a not-found message on error", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("404"));
    render(<FindMyTeam allocationId="alloc-1" />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "nobody@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /find my team/i }));
    await waitFor(() => expect(screen.getByText(/couldn't find that email/i)).toBeInTheDocument());
  });
});
