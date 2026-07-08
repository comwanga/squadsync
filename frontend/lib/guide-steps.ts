export interface GuideStep {
  id: string;
  title: string;
  caption: string;
  image: string; // path under /public
}

// Screenshots are 1280x800 (capture viewport); see scripts/capture-guide.mjs.
export const GUIDE_STEPS: GuideStep[] = [
  {
    id: "sign-in",
    title: "1. Sign in as organizer",
    caption: "Open your dashboard to create and manage events.",
    image: "/guide/01-login.png",
  },
  {
    id: "create-event",
    title: "2. Create an event",
    caption: "Click New Event, give it a name, and add a description — the description helps SquadSync group attendees more accurately.",
    image: "/guide/02-create-event.png",
  },
  {
    id: "activate",
    title: "3. Open your event",
    caption: "Your new event opens to its dashboard, where you can activate it and manage everything.",
    image: "/guide/03-event-dashboard.png",
  },
  {
    id: "share-qr",
    title: "4. Share the registration QR code",
    caption: "Open Attendees to get a QR code and link. Share it so people can register themselves.",
    image: "/guide/04-attendees-qr.png",
  },
  {
    id: "register",
    title: "5. Attendees register",
    caption: "Each person picks a Primary Strength (or 'Other' to type their own) and an Experience level — works for any team, any event.",
    image: "/guide/05-join-form.png",
  },
  {
    id: "configure",
    title: "6. (Optional) Tune the balance",
    caption: "Configure balancing weights and per-team strength requirements if you want finer control.",
    image: "/guide/06-configure.png",
  },
  {
    id: "generate",
    title: "7. Generate teams",
    caption: "Generate a draft preview, review the fairness metrics, then publish when ready.",
    image: "/guide/07-engine-results.png",
  },
  {
    id: "publish",
    title: "8. Publish & share results",
    caption: "Publish to announce teams, then export CSV/PDF or share the public results link.",
    image: "/guide/08-published.png",
  },
  {
    id: "payout",
    title: "9. Optional: Advanced Rewards",
    caption: "For events with prizes, open Advanced Rewards on a published team, run a dry check, then split the prize when ready.",
    image: "/guide/09-payout.png",
  },
  {
    id: "ai-categorize",
    title: "10. Behind the scenes: SquadSync sorts free-text answers",
    caption: `When someone picks “Other” and types their own strength, SquadSync categorizes it automatically before forming teams. The Attendees table shows each person's category and you can override any of them.`,
    image: "/guide/10-ai-category.png",
  },
];
