"use client";

import { useState, useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { PRIMARY_STRENGTHS, EXPERIENCE_LEVELS } from "@/lib/taxonomy";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Invalid email"),
  phone: z.string().optional(),
  primary_strength: z.enum([
    "technical", "design", "planning", "coordination",
    "communication", "research", "domain_expert", "other",
  ]),
  strength_other: z.string().optional(),
  experience_level: z.enum(["beginner", "intermediate", "advanced"]),
  npub: z.string().optional(),
  lightning_address: z.string().optional(),
}).refine(
  d => d.primary_strength !== "other" || (d.strength_other?.trim().length ?? 0) > 0,
  { message: "Please describe your strength", path: ["strength_other"] },
);

type FormData = z.infer<typeof schema>;

interface EventInfo {
  id: string;
  title: string;
  status: string;
  description?: string;
}

export function RegistrationForm({ event, slug }: { event: EventInfo; slug: string }) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, control, watch, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { primary_strength: "technical", experience_level: "intermediate" },
  });

  const selectedStrength = watch("primary_strength");

  useEffect(() => {
    const prefillLightningAddress = async () => {
      try {
        if (typeof window === "undefined") return;

        // Guard: don't overwrite a value the user already typed
        // (read current value from the DOM; setValue hasn't run yet at mount)
        let pk: string | null = null;

        if ("nostr" in window) {
          pk = await (window as Window & { nostr: { getPublicKey(): Promise<string> } }).nostr.getPublicKey();
        } else {
          const skHex = localStorage.getItem("squadsync:nostr_sk");
          if (!skHex) return;
          const hexToBytes = (hex: string): Uint8Array =>
            new Uint8Array(hex.match(/.{2}/g)!.map((b) => parseInt(b, 16)));
          const { getPublicKey } = await import("nostr-tools");
          pk = getPublicKey(hexToBytes(skHex));
        }

        if (!pk) return;

        const { SimplePool } = await import("nostr-tools/pool");
        const pool = new SimplePool();
        const relays = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band"];
        const evt = await pool.get(relays, { kinds: [0], authors: [pk] });
        pool.close(relays);

        if (evt) {
          const meta = JSON.parse(evt.content);
          const ln = meta.lud16 || meta.lightning_address;
          if (ln) {
            // Only prefill if the field is still empty
            const current = (document.getElementById("lightning_address") as HTMLInputElement | null)?.value;
            if (!current) {
              setValue("lightning_address", String(ln));
            }
          }
        }
      } catch {
        // Best-effort: silently no-op on any failure
      }
    };

    prefillLightningAddress();
  }, [setValue]);

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await fetchAPI(`/api/v1/events/${slug}/register`, { method: "POST", body: data });
      setSubmitted(true);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
        <CheckCircle2 className="h-16 w-16 text-green-500" />
        <h2 className="text-xl font-bold">You&apos;re registered!</h2>
        <p className="text-muted-foreground max-w-xs">
          Your registration for <strong>{event.title}</strong> has been confirmed. Teams will be announced soon.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="space-y-1">
        <Label htmlFor="name">Name</Label>
        <Input id="name" placeholder="Your full name" {...register("name")} />
        {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="you@example.com" {...register("email")} />
        {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="phone">Phone (optional)</Label>
        <Input id="phone" type="tel" placeholder="+1 555 000 0000" {...register("phone")} />
      </div>

      <div className="space-y-1">
        <Label htmlFor="npub">Nostr npub (optional)</Label>
        <Input id="npub" placeholder="npub1…" {...register("npub")} />
        <p className="text-xs text-muted-foreground">
          Paste your Nostr npub to be DM&apos;d your team. Otherwise you can look it up after results are posted.
        </p>
      </div>

      <div className="space-y-1">
        <Label htmlFor="lightning_address">Lightning address (optional)</Label>
        <Input id="lightning_address" placeholder="you@walletofsatoshi.com" {...register("lightning_address")} />
        <p className="text-xs text-muted-foreground">
          Where to send your share if your team wins a Bitcoin prize. Auto-filled from your Nostr profile when available.
        </p>
      </div>

      <div className="space-y-1">
        <Label>Primary Strength</Label>
        <Controller
          name="primary_strength"
          control={control}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger><SelectValue placeholder="Select your strength" /></SelectTrigger>
              <SelectContent>
                {PRIMARY_STRENGTHS.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {selectedStrength === "other" && (
        <div className="space-y-1">
          <Label htmlFor="strength_other">Describe your strength</Label>
          <Input id="strength_other" placeholder="e.g. Agronomist, GIS analyst, Teacher" {...register("strength_other")} />
          {errors.strength_other && <p className="text-sm text-red-500">{errors.strength_other.message}</p>}
        </div>
      )}

      <div className="space-y-1">
        <Label>Experience</Label>
        <Controller
          name="experience_level"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Experience">
              {EXPERIENCE_LEVELS.map(level => {
                const active = field.value === level.value;
                return (
                  <button
                    key={level.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => field.onChange(level.value)}
                    className={cn(
                      "rounded-md border px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    {level.label}
                  </button>
                );
              })}
            </div>
          )}
        />
      </div>

      <Button type="submit" className="w-full" size="lg" disabled={loading}>
        {loading ? "Submitting…" : "Join Event"}
      </Button>
    </form>
  );
}
