"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { useEvent, updateEvent, archiveEvent, deleteEvent } from "@/hooks/use-events";
import { formatEventDate } from "@/lib/format-date";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Users, Settings, Zap, ArrowRight, Archive, Trash2, Calendar } from "lucide-react";

export default function EventPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);
  const { event, isLoading } = useEvent(eventId);
  const { data: session } = useSession();
  const [activating, setActivating] = useState(false);
  const router = useRouter();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleArchive = async () => {
    if (!session?.accessToken) return;
    setBusy(true);
    try {
      await archiveEvent(session.accessToken, eventId);
      toast.success("Event archived");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to archive");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!session?.accessToken) return;
    setBusy(true);
    try {
      await deleteEvent(session.accessToken, eventId);
      toast.success("Event permanently deleted");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  };

  if (isLoading) return <div className="animate-pulse space-y-4"><div className="h-8 bg-slate-200 rounded w-1/3" /></div>;
  if (!event) return <p className="text-muted-foreground">Event not found</p>;

  const handleActivate = async () => {
    if (!session?.accessToken) return;
    setActivating(true);
    try {
      await updateEvent(session.accessToken, eventId, { status: "active" });
      toast.success("Registration is now open");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to open registration");
    } finally {
      setActivating(false);
    }
  };

  const quickActions = [
    { label: "Attendees", icon: Users, href: "attendees", description: "View participants & QR code" },
    { label: "Configure", icon: Settings, href: "configure", description: "Set allocation weights & rules" },
    { label: "Run Allocation", icon: Zap, href: "engine", description: "Generate balanced teams" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{event.title}</h1>
          {event.description && <p className="text-muted-foreground text-sm mt-1">{event.description}</p>}
          <p className="text-muted-foreground text-sm mt-1 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" /> {formatEventDate(event.event_at)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className="capitalize">{event.status}</Badge>
          {event.status === "draft" && (
            <Button size="sm" onClick={handleActivate} disabled={activating}>
              {activating ? "Opening…" : "Open Registration"}
            </Button>
          )}
          {event.status !== "archived" && (
            <Button size="sm" variant="outline" onClick={handleArchive} disabled={busy}>
              <Archive className="mr-1 h-4 w-4" /> Archive
            </Button>
          )}
          <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700" onClick={() => setConfirmDelete(true)} disabled={busy}>
            <Trash2 className="mr-1 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {quickActions.map(({ label, icon: Icon, href, description }) => (
          <Card key={href} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Icon className="h-4 w-4 text-primary" /> {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">{description}</p>
              <Button asChild variant="ghost" size="sm" className="p-0 h-auto">
                <Link href={`/dashboard/events/${eventId}/${href}`}>
                  Go <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete this event permanently?</DialogTitle>
            <DialogDescription>
              This removes <strong>{event.title}</strong> and all of its participants and
              results. This cannot be undone. To keep the record instead, use Archive.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmDelete(false)} disabled={busy}>Cancel</Button>
            <Button className="bg-red-600 hover:bg-red-700 text-white" onClick={handleDelete} disabled={busy}>
              {busy ? "Deleting…" : "Delete permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
