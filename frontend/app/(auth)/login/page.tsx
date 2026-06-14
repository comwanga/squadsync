import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { NostrConnect } from "@/components/auth/nostr-connect";
import { Logo } from "@/components/brand/logo";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <Logo priority className="h-10 w-auto mx-auto mb-2" />
          <CardDescription>
            No account needed — connect with your Nostr identity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <NostrConnect />
        </CardContent>
      </Card>
    </div>
  );
}
