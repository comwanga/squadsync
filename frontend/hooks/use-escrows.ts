import { fetchAPI } from "@/lib/api";

export interface EscrowItem {
  id: string;
  agent_coordinate: string;
  event_id: string | null;
  allocation_id: string | null;
  amount_sats: number;
  rail: string;
  status: string;
  release_policy: Record<string, unknown>;
  refund_policy: Record<string, unknown>;
  funding_request: string | null;
  created_at: string;
  funded_at: string | null;
  released_at: string | null;
}

export interface Escrow {
  id: string;
  organizer_id: string;
  agent_coordinate: string;
  event_id: string | null;
  allocation_id: string | null;
  team_id: string | null;
  amount_sats: number;
  rail: string;
  status: string;
  release_policy: Record<string, unknown>;
  refund_policy: Record<string, unknown>;
  dispute_policy: Record<string, unknown>;
  funding_request: string | null;
  nwc_uri: string | null;
  created_at: string;
  updated_at: string;
  funded_at: string | null;
  released_at: string | null;
}

export async function createEscrow(
  token: string,
  body: {
    agent_coordinate: string;
    event_id?: string;
    allocation_id?: string;
    team_id?: string;
    amount_sats: number;
    rail: string;
  },
): Promise<Escrow> {
  return fetchAPI<Escrow>("/api/v1/escrows", { method: "POST", body, token });
}

export async function fetchEscrows(
  token: string,
  status?: string,
): Promise<EscrowItem[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return fetchAPI<EscrowItem[]>(`/api/v1/escrows${qs}`, { token });
}

export async function fetchEscrow(
  token: string,
  id: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}`, { token });
}

export async function activateEscrow(
  token: string,
  id: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}/activate`, { method: "POST", token });
}

export async function fundEscrow(
  token: string,
  id: string,
  nwcUri?: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}/fund`, {
    method: "POST",
    body: { nwc_uri: nwcUri ?? null },
    token,
  });
}

export async function confirmFunded(
  token: string,
  id: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}/confirm-funded`, {
    method: "POST",
    token,
  });
}

export async function releaseEscrow(
  token: string,
  id: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}/release`, {
    method: "POST",
    token,
  });
}

export async function cancelEscrow(
  token: string,
  id: string,
): Promise<Escrow> {
  return fetchAPI<Escrow>(`/api/v1/escrows/${id}/cancel`, {
    method: "POST",
    token,
  });
}
