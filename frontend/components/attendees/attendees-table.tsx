"use client";

import { useState } from "react";
import useSWR from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { CONCRETE_STRENGTHS, EXPERIENCE_LEVELS } from "@/lib/taxonomy";
import { SourceBadge } from "@/components/attendees/source-badge";

interface Participant {
  id: string;
  name: string;
  email: string;
  primary_strength: string;
  strength_other?: string;
  normalized_strength?: string;
  strength_source: string;
  experience_level: string;
  composite_score?: number;
  registered_at: string;
}

const experienceColor: Record<string, string> = {
  beginner: "bg-green-100 text-green-800",
  intermediate: "bg-blue-100 text-blue-800",
  advanced: "bg-purple-100 text-purple-800",
};

export function AttendeesTable({ eventId }: { eventId: string }) {
  const { data: session } = useSession();
  const [search, setSearch] = useState("");
  const [strengthFilter, setStrengthFilter] = useState("all");
  const [experienceFilter, setExperienceFilter] = useState("all");

  const params = new URLSearchParams();
  if (strengthFilter !== "all") params.set("strength", strengthFilter);
  if (experienceFilter !== "all") params.set("experience", experienceFilter);

  const { data: participants = [], isLoading, mutate } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/participants`, params.toString(), session.accessToken] : null,
    ([path, q, token]) => fetchAPI<Participant[]>(`${path}?${q}`, { token })
  );

  // Strength/experience filters are server-side (query params); name/email search is
  // client-side within the current filtered set.
  const filtered = participants.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  async function saveCategory(id: string, normalized_strength: string) {
    if (!session?.accessToken) return;
    await fetchAPI(`/api/v1/events/${eventId}/participants/${id}`, {
      method: "PATCH", body: { normalized_strength }, token: session.accessToken,
    });
    mutate();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Search by name or email…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={strengthFilter} onValueChange={setStrengthFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All strengths" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All strengths</SelectItem>
            {CONCRETE_STRENGTHS.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={experienceFilter} onValueChange={setExperienceFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All levels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All levels</SelectItem>
            {EXPERIENCE_LEVELS.map(e => <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
        </div>
      ) : (
        <div className="border dark:border-slate-700 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b dark:border-slate-700">
                <tr>
                  {["Name", "Email", "Category", "Experience", "Source", "Score"].map(h => (
                    <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-slate-700">
                {filtered.length === 0 ? (
                  <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">No participants found</td></tr>
                ) : filtered.map(p => (
                  <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-3 font-medium whitespace-nowrap">{p.name}</td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{p.email}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Select value={p.normalized_strength ?? undefined} onValueChange={v => saveCategory(p.id, v)}>
                        <SelectTrigger className="h-8 w-44">
                          <SelectValue placeholder={p.strength_other ? `${p.strength_other} (pending)` : "Set category"} />
                        </SelectTrigger>
                        <SelectContent>
                          {CONCRETE_STRENGTHS.map(s => (
                            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${experienceColor[p.experience_level] ?? ""}`}>
                        {p.experience_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap"><SourceBadge source={p.strength_source} /></td>
                    <td className="px-4 py-3 font-mono whitespace-nowrap">{p.composite_score?.toFixed(2) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <p className="text-xs text-muted-foreground">{filtered.length} participant{filtered.length !== 1 ? "s" : ""}</p>
    </div>
  );
}
