"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { MessageSquare, Loader2 } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function FeedbackCard() {
  const { data: session } = useSession();
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!message.trim() || !session?.accessToken) return;
    setSending(true);
    try {
      await fetchAPI("/api/v1/feedback", {
        method: "POST",
        body: { message: message.trim() },
        token: session.accessToken,
      });
      toast.success("Thanks for the feedback!");
      setMessage("");
    } catch {
      toast.error("Couldn't send feedback. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <MessageSquare className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-base">Send feedback</CardTitle>
            <CardDescription>Tell us what&apos;s working or what could be better</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <label htmlFor="feedback" className="sr-only">Feedback</label>
        <textarea
          id="feedback"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={2000}
          rows={4}
          placeholder="Your feedback…"
          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button onClick={handleSend} disabled={sending || !message.trim()} className="w-full">
          {sending ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…</>
          ) : (
            "Send feedback"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
