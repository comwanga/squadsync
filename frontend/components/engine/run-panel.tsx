"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Wand2, Loader2 } from "lucide-react";
import { runAllocation } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Allocation } from "@/hooks/use-allocation";

const PASSES = [
  "Step 1 - Place experienced participants",
  "Step 2 - Balance remaining participants",
  "Step 3 - Check strength coverage",
  "Step 4 - Fill team sizes",
];

interface RunPanelProps {
  eventId: string;
  participantCount: number;
  onComplete: (allocation: Allocation) => void;
}

export function RunPanel({ eventId, participantCount, onComplete }: RunPanelProps) {
  const { data: session } = useSession();
  const [running, setRunning] = useState(false);
  const [currentPass, setCurrentPass] = useState(-1);

  const handleRun = async () => {
    if (!session?.accessToken) return;
    setRunning(true);
    try {
      for (let i = 0; i < PASSES.length; i++) {
        setCurrentPass(i);
        await new Promise(r => setTimeout(r, 400));
      }
      const allocation = await runAllocation(session.accessToken, eventId);
      onComplete(allocation);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Allocation failed");
      setCurrentPass(-1);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle className="text-base">Team preview</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {participantCount} participants ready for allocation.
          SquadSync will build a reproducible draft that you can review before publishing.
        </p>
        <p className="text-xs text-muted-foreground">
          Free-text &quot;Other&quot; strengths are grouped automatically before teams are generated.
        </p>

        {running && (
          <ul className="space-y-2">
            {PASSES.map((pass, i) => (
              <li key={i} className={`flex items-center gap-2 text-sm ${i <= currentPass ? "text-foreground" : "text-muted-foreground"}`}>
                {i < currentPass ? (
                  <span className="h-4 w-4 rounded-full bg-primary flex-shrink-0" />
                ) : i === currentPass ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                ) : (
                  <span className="h-4 w-4 rounded-full border border-slate-300 flex-shrink-0" />
                )}
                {pass}
              </li>
            ))}
          </ul>
        )}

        <Button onClick={handleRun} disabled={running || participantCount < 2} className="w-full">
          {running ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running…</>
          ) : (
            <><Wand2 className="mr-2 h-4 w-4" /> Generate Teams</>
          )}
        </Button>
        {participantCount < 2 && (
          <p className="text-xs text-red-500">At least 2 participants required</p>
        )}
      </CardContent>
    </Card>
  );
}
