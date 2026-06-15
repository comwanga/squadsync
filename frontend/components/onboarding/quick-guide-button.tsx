"use client";

import { startTransition, useEffect, useState } from "react";
import Link from "next/link";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const SEEN_KEY = "squadsync.guideSeen";

export function QuickGuideButton() {
  // Default hidden so server and first client paint match (no hydration mismatch).
  const [showDot, setShowDot] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(SEEN_KEY) !== "1") {
      startTransition(() => setShowDot(true));
    }
  }, []);

  const markSeen = () => {
    localStorage.setItem(SEEN_KEY, "1");
    setShowDot(false);
  };

  return (
    <Link
      href="/dashboard/settings/guide"
      onClick={markSeen}
      className={cn(
        "relative inline-flex items-center gap-1.5 rounded-md border border-input bg-background",
        "px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
      )}
    >
      <HelpCircle className="h-4 w-4" />
      Quick guide
      {showDot && (
        <span
          data-testid="guide-dot"
          aria-label="New"
          className="absolute -right-1 -top-1 flex h-2.5 w-2.5"
        >
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
        </span>
      )}
    </Link>
  );
}
