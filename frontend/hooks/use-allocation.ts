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
  role: string;
  skill_level: string;
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
