"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Invalid email"),
  phone: z.string().optional(),
  skill_level: z.enum(["beginner", "intermediate", "advanced", "professional"]).refine(Boolean, "Select your skill level"),
  role: z.enum(["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"]).refine(Boolean, "Select your preferred role"),
  years_experience: z.number().int().min(0),
});

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
  const { register, handleSubmit, control, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { years_experience: 0, skill_level: "beginner" as const, role: "frontend" as const },
  });

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
        <Label>Skill Level</Label>
        <Controller
          name="skill_level"
          control={control}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger><SelectValue placeholder="Select your level" /></SelectTrigger>
              <SelectContent>
                {["beginner","intermediate","advanced","professional"].map(s => (
                  <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.skill_level && <p className="text-sm text-red-500">{errors.skill_level.message}</p>}
      </div>

      <div className="space-y-1">
        <Label>Preferred Role</Label>
        <Controller
          name="role"
          control={control}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger><SelectValue placeholder="Select your role" /></SelectTrigger>
              <SelectContent>
                {["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"].map(r => (
                  <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.role && <p className="text-sm text-red-500">{errors.role.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="years_experience">Years of Experience</Label>
        <Input id="years_experience" type="number" min={0} {...register("years_experience", { valueAsNumber: true })} />
      </div>

      <Button type="submit" className="w-full" size="lg" disabled={loading}>
        {loading ? "Submitting…" : "Join Event"}
      </Button>
    </form>
  );
}
