import Image from "next/image";
import { GUIDE_STEPS } from "@/lib/guide-steps";
import { Breadcrumb } from "@/components/layout/breadcrumb";

export default function GuidePage() {
  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <Breadcrumb items={[{ label: "Settings", href: "/dashboard/settings" }, { label: "Guide" }]} />
        <h1 className="text-2xl font-bold tracking-tight mt-2">How SquadSync works</h1>
        <p className="text-sm text-muted-foreground mt-1">A quick walkthrough from sign-in to published teams.</p>
      </div>

      <ol className="space-y-10">
        {GUIDE_STEPS.map(step => (
          <li key={step.id} className="space-y-3">
            <h2 className="text-lg font-semibold">{step.title}</h2>
            <p className="text-sm text-muted-foreground">{step.caption}</p>
            <Image
              src={step.image}
              alt={step.title}
              width={1280}
              height={800}
              className="w-full h-auto rounded-lg border dark:border-slate-700"
            />
          </li>
        ))}
      </ol>
    </div>
  );
}
