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
    title: "1. Sign in with Nostr",
    caption: "No account needed — connect with your Nostr identity to reach your dashboard.",
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
    caption: "Run the engine to form balanced teams. Free-text 'Other' strengths are normalized automatically before allocation.",
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
    title: "9. Pay out the winning team in Bitcoin",
    caption: "On a published allocation, choose a winning team and “Pay out”. Enter a prize in sats and connect a wallet via Nostr Wallet Connect (NIP-47) — SquadSync splits the pot evenly and pays each winner over Lightning, showing live per-member status.",
    image: "/guide/09-payout.png",
  },
  {
    id: "ai-categorize",
    title: "10. Behind the scenes: SquadSync sorts free-text answers",
    caption: `When someone picks “Other” and types their own strength, SquadSync categorizes it automatically before forming teams — by AI when an API key is set, deterministically otherwise. The Attendees table shows each person’s category and its source (AI / Auto / Manual), and you can override any of them.`,
    image: "/guide/10-ai-category.png",
  },
];
