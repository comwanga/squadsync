import useSWR, { mutate } from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";

export interface Event {
  id: string;
  title: string;
  description?: string;
  participant_limit?: number;
  team_count: number;
  status: string;
  registration_slug: string;
}

function useToken() {
  const { data: session, status } = useSession();
  return { token: session?.accessToken, isSessionLoading: status === "loading" };
}

export function useEvents() {
  const { token, isSessionLoading } = useToken();
  const { data, error, isLoading } = useSWR(
    token ? ["/api/v1/events", token] : null,
    ([path, t]) => fetchAPI<Event[]>(path, { token: t })
  );
  return { events: data ?? [], error, isLoading: isLoading || isSessionLoading };
}

export function useEvent(eventId: string | null) {
  const { token, isSessionLoading } = useToken();
  const { data, error, isLoading } = useSWR(
    token && eventId ? [`/api/v1/events/${eventId}`, token] : null,
    ([path, t]) => fetchAPI<Event>(path, { token: t })
  );
  return { event: data, error, isLoading: isLoading || isSessionLoading };
}

export interface CreateEventPayload {
  title: string;
  description?: string;
  team_count: number;
  participant_limit?: number;
}

export async function createEvent(token: string, payload: CreateEventPayload) {
  const result = await fetchAPI<Event>("/api/v1/events", {
    method: "POST",
    body: payload,
    token,
  });
  mutate(["/api/v1/events", token]);
  return result;
}

export async function updateEvent(token: string, eventId: string, payload: Partial<CreateEventPayload & { status: string }>) {
  const result = await fetchAPI<Event>(`/api/v1/events/${eventId}`, {
    method: "PATCH",
    body: payload,
    token,
  });
  mutate([`/api/v1/events/${eventId}`, token]);
  mutate(["/api/v1/events", token]);
  return result;
}
