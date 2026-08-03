"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { useAllocationConfig, saveAllocationConfig, type AllocationConfig } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { CONCRETE_STRENGTHS } from "@/lib/taxonomy";

interface Constraint { role: string; min: number; }

export function ConfigForm({ eventId }: { eventId: string }) {
  const { config, error, isLoading } = useAllocationConfig(eventId);

  if (isLoading) return <div className="animate-pulse h-64 bg-slate-100 rounded-lg" />;
  if (error || !config) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-200">
        Configuration could not be loaded. Refresh before making changes.
      </div>
    );
  }

  // Remount (and re-seed local state) whenever the loaded config identity changes,
  // instead of syncing fetched data into state via an effect.
  return <ConfigFormFields key={config.id} eventId={eventId} initial={config} />;
}

function ConfigFormFields({ eventId, initial }: { eventId: string; initial: AllocationConfig }) {
  const { data: session } = useSession();
  const [constraints, setConstraints] = useState<Constraint[]>(
    Object.entries(initial.role_constraints).map(([role, min]) => ({ role, min: min as number }))
  );
  const [saving, setSaving] = useState(false);

  const addConstraint = () => setConstraints(c => [...c, { role: "technical", min: 1 }]);
  const removeConstraint = (i: number) => setConstraints(c => c.filter((_, idx) => idx !== i));
  const updateConstraint = (i: number, field: keyof Constraint, value: string | number) =>
    setConstraints(c => c.map((item, idx) => idx === i ? { ...item, [field]: value } : item));

  const handleSave = async () => {
    if (!session?.accessToken) return;
    setSaving(true);
    try {
      const role_constraints = Object.fromEntries(constraints.map(c => [c.role, c.min]));
      await saveAllocationConfig(session.accessToken, eventId, {
        role_constraints,
      });
      toast.success("Configuration saved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Role Constraints</CardTitle>
            <Button variant="outline" size="sm" onClick={addConstraint}>
              <Plus className="mr-1 h-3.5 w-3.5" /> Add Constraint
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {constraints.length === 0 ? (
            <p className="text-sm text-muted-foreground">No constraints — engine will balance freely</p>
          ) : constraints.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <Select value={c.role} onValueChange={v => updateConstraint(i, "role", v)}>
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONCRETE_STRENGTHS.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground whitespace-nowrap">min</span>
              <Input
                type="number" min={1} max={10}
                value={c.min}
                onChange={e => updateConstraint(
                  i,
                  "min",
                  Math.min(10, Math.max(1, Number(e.target.value) || 1)),
                )}
                className="w-16"
              />
              <Button variant="ghost" size="icon" onClick={() => removeConstraint(i)}>
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Saving…" : "Save Configuration"}
      </Button>
    </div>
  );
}
