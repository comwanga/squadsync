import useSWR, { mutate } from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";

export interface AllocationConfig {
  id: string;
  event_id: string;
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

export interface TeamRationale {
  title: string;
  summary: string;
  strengths: string[];
  gaps: string[];
}

export interface Team {
  id: string;
  name: string;
  fairness_score?: number;
  skill_score?: number;
  role_balance_score?: number;
  members: TeamMember[];
  rationale?: TeamRationale | null;
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
  const { data, error, isLoading } = useSWR(
    token ? [`/api/v1/events/${eventId}/config`, token] : null,
    ([path, t]) => fetchAPI<AllocationConfig>(path, { token: t })
  );
  return { config: data, error, isLoading: isLoading || isSessionLoading };
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

export interface PayoutPreflight {
  team_id: string;
  total_sats: number;
  items: Array<{
    participant_id: string;
    name: string;
    lightning_address: string;
    amount_sats: number;
  }>;
}

export interface RewardClaim {
  id: string;
  token: string;
  allocation_id: string;
  team_id: string;
  participant_id: string;
  name: string;
  amount_sats: number;
  lightning_address: string | null;
  status: string;
  expires_at: string;
  claim_url: string;
}

export interface RewardClaimBatch {
  team_id: string;
  total_sats: number;
  items: RewardClaim[];
}

export interface PublicRewardClaim {
  token: string;
  participant_name: string;
  team_name: string;
  amount_sats: number;
  status: string;
  expires_at: string;
  lightning_address: string | null;
}

export async function preflightPayout(
  token: string,
  allocationId: string,
  body: { team_id: string; total_sats: number; addresses?: Record<string, string> }
) {
  return fetchAPI<PayoutPreflight>(
    `/api/v1/allocations/${allocationId}/payouts/preflight`,
    { method: "POST", body, token }
  );
}

export async function createPayout(
  token: string,
  allocationId: string,
  body: { team_id: string; total_sats: number; addresses?: Record<string, string> }
) {
  // Self-custody: no nwc is sent. The server returns pending items for the browser to pay.
  return fetchAPI<Payout>(`/api/v1/allocations/${allocationId}/payouts`, { method: "POST", body, token });
}

export async function createRewardClaims(
  token: string,
  allocationId: string,
  body: { team_id: string; total_sats: number }
) {
  return fetchAPI<RewardClaimBatch>(
    `/api/v1/allocations/${allocationId}/reward-claims`,
    { method: "POST", body, token }
  );
}

export async function getRewardClaim(token: string) {
  return fetchAPI<PublicRewardClaim>(`/api/v1/allocations/reward-claims/${token}`);
}

export async function submitRewardClaim(token: string, lightningAddress: string) {
  return fetchAPI<PublicRewardClaim>(
    `/api/v1/allocations/reward-claims/${token}`,
    { method: "POST", body: { lightning_address: lightningAddress } }
  );
}

export async function reportPayoutItemResult(
  token: string,
  payoutId: string,
  itemId: string,
  bolt11: string,
  preimage: string
) {
  return fetchAPI<Payout>(
    `/api/v1/allocations/payouts/${payoutId}/items/${itemId}/result`,
    { method: "POST", body: { bolt11, preimage }, token }
  );
}

export async function reportPayoutItemFailed(
  token: string,
  payoutId: string,
  itemId: string,
  error: string
) {
  return fetchAPI<Payout>(
    `/api/v1/allocations/payouts/${payoutId}/items/${itemId}/failed`,
    { method: "POST", body: { error }, token }
  );
}

export async function generateRationales(token: string, allocationId: string) {
  return fetchAPI<Record<string, TeamRationale>>(
    `/api/v1/allocations/${allocationId}/rationale`,
    { method: "POST", token }
  );
}
