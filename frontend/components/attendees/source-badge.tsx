const STYLES: Record<string, { label: string; cls: string }> = {
  ai: { label: "AI", cls: "bg-violet-100 text-violet-800" },
  fallback: { label: "Auto", cls: "bg-slate-100 text-slate-700" },
  manual: { label: "Manual", cls: "bg-blue-100 text-blue-800" },
};

export function SourceBadge({ source }: { source: string }) {
  const s = STYLES[source];
  if (!s) return <span className="text-xs text-muted-foreground">{source}</span>;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>;
}
