"use client";

import { useRef, useState } from "react";
import useSWR from "swr";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Download, FileUp } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { CONCRETE_STRENGTHS, EXPERIENCE_LEVELS } from "@/lib/taxonomy";
import { SourceBadge } from "@/components/attendees/source-badge";
import { isKnownStrength, categoryPlaceholder } from "@/lib/category-display";

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
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  async function downloadCsv(path: string, filename: string) {
    if (!session?.accessToken) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
        headers: { Authorization: `Bearer ${session.accessToken}` },
      });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Download failed");
    }
  }

  function downloadTemplate() {
    const csv = "name,email,phone,primary_strength,strength_other,experience_level,notification_id,prize_address\n";
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "squadsync-participants-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function importCsv(file: File) {
    if (!session?.accessToken) return;
    setImporting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/events/${eventId}/participants/import/csv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.accessToken}` },
        body: form,
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? `Import failed (${res.status})`);
      if (body.errors?.length) {
        toast.error(`Import failed: ${body.errors[0]}`);
      } else {
        toast.success(`Imported ${body.created} new, updated ${body.updated}, skipped ${body.skipped}`);
        mutate();
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
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
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={downloadTemplate}>
            <Download className="mr-2 h-4 w-4" /> Template
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => downloadCsv(`/api/v1/events/${eventId}/participants/export/csv`, `squadsync-participants-${eventId}.csv`)}
          >
            <Download className="mr-2 h-4 w-4" /> Export
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={importing}>
            <FileUp className="mr-2 h-4 w-4" /> {importing ? "Importing..." : "Import"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={e => {
              const file = e.target.files?.[0];
              if (file) importCsv(file);
            }}
          />
        </div>
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
                      <Select
                        value={isKnownStrength(p.normalized_strength) ? p.normalized_strength : undefined}
                        onValueChange={v => saveCategory(p.id, v)}
                      >
                        <SelectTrigger className="h-8 w-44">
                          <SelectValue placeholder={categoryPlaceholder(p)} />
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
