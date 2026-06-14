"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { createEvent } from "@/hooks/use-events";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  team_count: z.coerce.number().int().min(2, "Minimum 2 teams"),
  participant_limit: z.preprocess(
    val => (val === "" || val === null || val === undefined ? undefined : val),
    z.coerce.number().int().min(1).optional()
  ),
});

type FormInput = z.input<typeof schema>;
type FormData = z.output<typeof schema>;

export function CreateEventDialog() {
  const { data: session } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormInput, unknown, FormData>({
    resolver: zodResolver(schema),
    defaultValues: { team_count: 5 },
  });

  const onSubmit = async (data: FormData) => {
    if (!session?.accessToken) return;
    setLoading(true);
    try {
      const event = await createEvent(session.accessToken, {
        title: data.title,
        description: data.description,
        team_count: data.team_count,
        participant_limit: data.participant_limit,
      });
      setOpen(false);
      reset();
      router.push(`/dashboard/events/${event.id}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create event");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> New Event
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Event</DialogTitle>
          <DialogDescription>
            Set up a new event. You can edit these details later.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="title">Event Name</Label>
            <Input id="title" placeholder="Hackathon 2026" {...register("title")} />
            {errors.title && <p className="text-sm text-red-500">{errors.title.message}</p>}
          </div>
          <div className="space-y-1">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              rows={3}
              placeholder="What is this event about? e.g. Build AI + satellite tools to improve crop yields."
              className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              {...register("description")}
            />
            <p className="text-xs text-muted-foreground">
              Describe the event — this helps SquadSync group attendees more accurately.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="team_count">Number of Teams</Label>
              <Input id="team_count" type="number" min={2} {...register("team_count")} />
              {errors.team_count && <p className="text-sm text-red-500">{errors.team_count.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="participant_limit">Max Participants</Label>
              <Input id="participant_limit" type="number" min={1} placeholder="No limit" {...register("participant_limit")} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating…" : "Create Event"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
