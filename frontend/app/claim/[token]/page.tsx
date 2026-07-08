import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Logo } from "@/components/brand/logo";
import { RewardClaimForm } from "@/components/engine/reward-claim-form";
import { fetchAPI } from "@/lib/api";
import type { PublicRewardClaim } from "@/hooks/use-allocation";

async function getClaim(token: string): Promise<PublicRewardClaim | null> {
  try {
    return await fetchAPI<PublicRewardClaim>(`/api/v1/allocations/reward-claims/${token}`);
  } catch {
    return null;
  }
}

export default async function RewardClaimPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  let claim = null;

  claim = await getClaim(token);

  if (!claim) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-sm text-center">
          <CardContent className="py-8">
            <p className="text-lg font-semibold">Reward link not found</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Ask the organizer for a fresh claim QR.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-start justify-center bg-slate-50 p-4 pt-8">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <Logo priority className="mx-auto mb-2 h-9 w-auto" />
          <CardTitle>Claim reward</CardTitle>
          <CardDescription>
            Add the Lightning Address where this reward should be sent.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RewardClaimForm claim={claim} />
        </CardContent>
      </Card>
    </div>
  );
}
