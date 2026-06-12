import Link from "next/link";
import { Calendar, Users, ArrowRight } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Event } from "@/hooks/use-events";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  draft: "secondary",
  active: "default",
  allocated: "outline",
  archived: "destructive",
};

export function EventCard({ event }: { event: Event }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-base font-semibold line-clamp-1">{event.title}</CardTitle>
          <Badge variant={statusVariant[event.status] ?? "secondary"} className="ml-2 capitalize text-xs">
            {event.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {event.participant_limit ? `Max ${event.participant_limit}` : "No limit"}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {event.team_count} teams
          </span>
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild variant="ghost" size="sm" className="ml-auto">
          <Link href={`/dashboard/events/${event.id}`}>
            Manage <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
