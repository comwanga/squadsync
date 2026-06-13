import { fetchAPI } from "@/lib/api";
import { RegistrationForm } from "@/components/registration/registration-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface EventInfo {
  id: string;
  title: string;
  status: string;
  description?: string;
}

async function getEvent(slug: string): Promise<EventInfo | null> {
  try {
    return await fetchAPI<EventInfo>(`/api/v1/events/${slug}/info`);
  } catch {
    return null;
  }
}

export default async function JoinPage({ params }: { params: { slug: string } }) {
  const event = await getEvent(params.slug);

  if (!event) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-sm text-center">
          <CardContent className="pt-8 pb-8">
            <p className="text-lg font-semibold">Event not found</p>
            <p className="text-muted-foreground text-sm mt-1">This registration link may have expired or be invalid.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (event.status !== "active") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-sm text-center">
          <CardContent className="pt-8 pb-8">
            <p className="text-lg font-semibold">{event.title}</p>
            <p className="text-muted-foreground text-sm mt-1">
              Registration is currently {event.status === "allocated" ? "closed — teams have been formed" : "not open"}.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-start justify-center p-4 pt-8">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="text-2xl font-bold text-primary mb-1">SquadSync</div>
          <CardTitle>{event.title}</CardTitle>
          {event.description && <CardDescription>{event.description}</CardDescription>}
        </CardHeader>
        <CardContent>
          <RegistrationForm event={event} slug={params.slug} />
        </CardContent>
      </Card>
    </div>
  );
}
