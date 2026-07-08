import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";
import { auth } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "SquadSync - Fair Team Generator",
  description: "Simple team formation for hackathons, workshops, and events",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await auth().catch(() => null);
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <Providers session={session}>
          {children}
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
