import useSWR, { mutate } from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";

export interface AllocationConfig {
  id: string;
  event_id: string;
  weight_experience: number;
  weight_skill: number;
  role_constraints: Record<string, number>;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  normalized_strength?: string;
  experience_level: string;
  composite_score?: number;
}

export interface Team {
  id: string;
  name: string;
  fairness_score?: number;
  skill_score?: number;
  role_balance_score?: number;
  members: TeamMember[];
}

export interface Allocation {
  id: string;
  event_id: string;
  snapshot_hash: string;
  status: string;
  constraint_warnings: Record<string, string[]>;
  ai_normalized?: number;
  auto_normalized?: number;
  teams: Team[];
}

function useToken() {
  const { data: session, status } = useSession();
  return { token: session?.accessToken, isSessionLoading: status === "loading" };
}

export function useAllocationConfig(eventId: string) {
  const { token, isSessionLoading } = useToken();
  const { data, isLoading } = useSWR(
    token ? [`/api/v1/events/${eventId}/config`, token] : null,
    ([path, t]) => fetchAPI<AllocationConfig>(path, { token: t })
  );
  return { config: data, isLoading: isLoading || isSessionLoading };
}

export async function saveAllocationConfig(token: string, eventId: string, payload: Partial<AllocationConfig>) {
  const result = await fetchAPI<AllocationConfig>(`/api/v1/events/${eventId}/config`, {
    method: "PUT",
    body: payload,
    token,
  });
  mutate([`/api/v1/events/${eventId}/config`, token]);
  return result;
}

export async function runAllocation(token: string, eventId: string) {
  return fetchAPI<Allocation>(`/api/v1/events/${eventId}/allocate`, { method: "POST", token });
}

export async function publishAllocation(token: string, eventId: string, allocationId: string) {
  return fetchAPI(`/api/v1/events/${eventId}/allocations/${allocationId}/publish`, { method: "POST", token });
}

export async function moveMember(token: string, allocationId: string, participantId: string, teamId: string) {
  return fetchAPI<Allocation>(
    `/api/v1/allocations/${allocationId}/members/${participantId}`,
    { method: "PATCH", body: { team_id: teamId }, token }
  );
}

export async function regenerateAllocation(token: string, eventId: string) {
  // The allocate endpoint reseeds and replaces the draft, so this yields a new draft.
  return runAllocation(token, eventId);
}

export interface PayoutItem {
  id: string;
  participant_id: string;
  lightning_address: string | null;
  amount_sats: number;
  status: string;
  preimage: string | null;
  error: string | null;
}

export interface Payout {
  id: string;
  event_id: string;
  allocation_id: string;
  team_label: string;
  total_sats: number;
  status: string;
  items: PayoutItem[];
}

export async function createPayout(
  token: string,
  allocationId: string,
  body: { team_id: string; total_sats: number; nwc: string; addresses?: Record<string, string> }
) {
  return fetchAPI<Payout>(`/api/v1/allocations/${allocationId}/payouts`, { method: "POST", body, token });
}

export async function retryPayout(
  token: string,
  payoutId: string,
  nwc: string,
  addresses?: Record<string, string>
) {
  return fetchAPI<Payout>(`/api/v1/allocations/payouts/${payoutId}/retry`, {
    method: "POST",
    body: { nwc, ...(addresses && Object.keys(addresses).length > 0 ? { addresses } : {}) },
    token,
  });
}
