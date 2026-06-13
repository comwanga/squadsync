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

interface Participant {
  id: string;
  name: string;
  email: string;
  role: string;
  skill_level: string;
  years_experience: number;
  composite_score?: number;
  registered_at: string;
}

const skillColor: Record<string, string> = {
  beginner: "bg-green-100 text-green-800",
  intermediate: "bg-blue-100 text-blue-800",
  advanced: "bg-purple-100 text-purple-800",
  professional: "bg-orange-100 text-orange-800",
};

export function AttendeesTable({ eventId }: { eventId: string }) {
  const { data: session } = useSession();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [skillFilter, setSkillFilter] = useState("all");

  const params = new URLSearchParams();
  if (roleFilter !== "all") params.set("role", roleFilter);
  if (skillFilter !== "all") params.set("skill", skillFilter);

  const { data: participants = [], isLoading } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/participants`, params.toString(), session.accessToken] : null,
    ([path, q, token]) => fetchAPI<Participant[]>(`${path}?${q}`, { token })
  );

  // Role/skill filters are server-side (query params); name/email search is client-side
  // within the current filtered set.
  const filtered = participants.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Search by name or email…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            {["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"]
              .map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={skillFilter} onValueChange={setSkillFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All levels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All levels</SelectItem>
            {["beginner","intermediate","advanced","professional"]
              .map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
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
                  {["Name", "Email", "Role", "Skill", "Exp.", "Score"].map(h => (
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
                    <td className="px-4 py-3 capitalize whitespace-nowrap">{p.role}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${skillColor[p.skill_level]}`}>
                        {p.skill_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{p.years_experience}y</td>
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
