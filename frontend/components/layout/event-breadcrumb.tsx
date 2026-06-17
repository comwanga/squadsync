"use client";

import { useEvent } from "@/hooks/use-events";
import { Breadcrumb, type BreadcrumbItem } from "@/components/layout/breadcrumb";

// Fixed-size placeholder so swapping in the real title never shifts the layout.
const titleSkeleton = (
  <span
    data-testid="breadcrumb-title-skeleton"
    aria-hidden
    className="inline-block h-4 w-24 align-middle rounded bg-muted animate-pulse"
  />
);

function buildItems(
  eventId: string,
  titleLabel: BreadcrumbItem["label"],
  current?: string,
): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [
    { label: "Events", href: "/dashboard/events" },
    current
      ? { label: titleLabel, href: `/dashboard/events/${eventId}` }
      : { label: titleLabel },
  ];
  if (current) items.push({ label: current });
  return items;
}

// Pure presentation: the page supplies the title it already loaded. Renders a
// skeleton until `title` is defined (e.g. a client page's first paint).
export function EventBreadcrumb({
  eventId,
  title,
  current,
}: {
  eventId: string;
  title?: string;
  current?: string;
}) {
  return <Breadcrumb items={buildItems(eventId, title ?? titleSkeleton, current)} />;
}

// Self-resolving: for pages that don't otherwise load the event (the engine
// page and the server-rendered configure page). Skeleton while loading; "Event"
// only as a rare loaded-but-missing fallback (the page itself 404s then).
export function EventBreadcrumbAuto({
  eventId,
  current,
}: {
  eventId: string;
  current?: string;
}) {
  const { event, isLoading } = useEvent(eventId);
  const titleLabel: BreadcrumbItem["label"] =
    isLoading && !event ? titleSkeleton : (event?.title ?? "Event");
  return <Breadcrumb items={buildItems(eventId, titleLabel, current)} />;
}
