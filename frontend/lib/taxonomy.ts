// Mirror of backend app/core/taxonomy.py — keep in sync.
export const PRIMARY_STRENGTHS = [
  { value: "technical", label: "Technical / Hands-on" },
  { value: "design", label: "Design / Creative" },
  { value: "planning", label: "Planning / Strategy" },
  { value: "coordination", label: "Coordination / Operations" },
  { value: "communication", label: "Communication / Outreach" },
  { value: "research", label: "Research / Analysis" },
  { value: "domain_expert", label: "Domain Expert" },
  { value: "other", label: "Other (type your own)" },
] as const;

// Concrete categories (excludes "other") — used by the organizer override control.
export const CONCRETE_STRENGTHS = PRIMARY_STRENGTHS.filter(s => s.value !== "other");

export const EXPERIENCE_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const;

export type PrimaryStrength = (typeof PRIMARY_STRENGTHS)[number]["value"];
