import Image from "next/image";
import { cn } from "@/lib/utils";

/**
 * SquadSync brand assets. Two variants, both with transparent backgrounds:
 *   <Logo>     full horizontal lockup (mark + wordmark) — headers, login, sidebar
 *   <LogoMark> hexagon mark only — QR center, mobile chrome, collapsed sidebar
 *
 * Source assets live in public/ (squadsync-logo.png, squadsync-mark.png).
 * App-icon variants (favicon/icon/apple-icon) are file-convention files in app/.
 */

const LOGO_INTRINSIC = { width: 700, height: 200 } as const;
const MARK_INTRINSIC = { width: 512, height: 512 } as const;

export function Logo({ className, priority }: { className?: string; priority?: boolean }) {
  return (
    <Image
      src="/squadsync-logo.png"
      alt="SquadSync"
      {...LOGO_INTRINSIC}
      priority={priority}
      className={cn("h-8 w-auto", className)}
    />
  );
}

export function LogoMark({ className, priority }: { className?: string; priority?: boolean }) {
  return (
    <Image
      src="/squadsync-mark.png"
      alt="SquadSync"
      {...MARK_INTRINSIC}
      priority={priority}
      className={cn("h-8 w-8", className)}
    />
  );
}
