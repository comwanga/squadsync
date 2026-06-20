import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TeamCard } from "@/components/engine/team-card";
import type { Team } from "@/hooks/use-allocation";

const team: Team = {
  id: "t1", name: "Team 01", fairness_score: 80, skill_score: 75, role_balance_score: 90,
  members: [{ id: "m1", name: "Ada", email: "a@x.com", experience_level: "advanced",
              normalized_strength: "technical" }],
  rationale: { title: "Build squad", summary: "Strong delivery.",
               strengths: ["2 advanced engineers"], gaps: ["limited outreach"] },
};

describe("TeamCard rationale", () => {
  it("renders the rationale summary and strengths/gaps when present", () => {
    render(<TeamCard team={team} />);
    expect(screen.getByText("Strong delivery.")).toBeInTheDocument();
    expect(screen.getByText("2 advanced engineers")).toBeInTheDocument();
    expect(screen.getByText("limited outreach")).toBeInTheDocument();
  });

  it("renders no rationale block when absent", () => {
    render(<TeamCard team={{ ...team, rationale: null }} />);
    expect(screen.queryByText("Strong delivery.")).not.toBeInTheDocument();
  });
});
