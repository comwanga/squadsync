import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NostrConnect } from "@/components/auth/nostr-connect";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">SquadSync</CardTitle>
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
