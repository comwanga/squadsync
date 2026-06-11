# SquadSync Phase 1 — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete SquadSync Next.js frontend — auth pages, organizer dashboard shell, event management, attendees + QR display, allocation engine UI, and the public mobile registration form.

**Architecture:** Next.js 14 App Router with route groups `(auth)` and `(dashboard)`. NextAuth.js v5 manages sessions; a central `fetchAPI()` wrapper forwards JWTs to the FastAPI backend. shadcn/ui + Tailwind CSS 3 for all UI. SWR for data fetching. Tests use Vitest + @testing-library/react.

**Prerequisites:** Backend plan must be complete and running at `http://localhost:8000`. Copy `.env.local.example` → `.env.local` and fill in `NEXTAUTH_SECRET` and `NEXT_PUBLIC_API_URL`.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS 3, shadcn/ui, NextAuth.js v5, SWR, react-hook-form, zod, react-qr-code, Vitest, @testing-library/react

---

## File Map

| File | Responsibility |
|------|----------------|
| `frontend/package.json` | Dependencies |
| `frontend/next.config.js` | Next.js config |
| `frontend/tailwind.config.ts` | Tailwind config |
| `frontend/.env.local.example` | Required env vars |
| `frontend/app/layout.tsx` | Root layout (SessionProvider, Toaster) |
| `frontend/app/(auth)/login/page.tsx` | Login page |
| `frontend/app/(auth)/register/page.tsx` | Register page |
| `frontend/app/(dashboard)/layout.tsx` | Dashboard shell |
| `frontend/app/(dashboard)/page.tsx` | Overview hub |
| `frontend/app/(dashboard)/events/[eventId]/page.tsx` | Event dashboard |
| `frontend/app/(dashboard)/events/[eventId]/attendees/page.tsx` | Attendees + QR |
| `frontend/app/(dashboard)/events/[eventId]/configure/page.tsx` | Allocation config |
| `frontend/app/(dashboard)/events/[eventId]/engine/page.tsx` | Engine run + results |
| `frontend/app/join/[slug]/page.tsx` | Public registration |
| `frontend/app/results/[allocationId]/page.tsx` | Public results (share link) |
| `frontend/components/layout/sidebar.tsx` | Collapsible sidebar |
| `frontend/components/layout/topbar.tsx` | Top bar |
| `frontend/components/auth/login-form.tsx` | Login form |
| `frontend/components/auth/register-form.tsx` | Register form |
| `frontend/components/events/event-card.tsx` | Event summary card |
| `frontend/components/events/create-event-dialog.tsx` | Create event dialog |
| `frontend/components/attendees/attendees-table.tsx` | Paginated attendee table |
| `frontend/components/attendees/qr-display.tsx` | QR code + download |
| `frontend/components/configure/config-form.tsx` | Weights + constraint builder |
| `frontend/components/engine/run-panel.tsx` | Pre-run summary |
| `frontend/components/engine/results-grid.tsx` | Team cards grid |
| `frontend/components/engine/team-card.tsx` | Individual team card |
| `frontend/components/registration/registration-form.tsx` | Public registration form |
| `frontend/lib/api.ts` | `fetchAPI()` wrapper |
| `frontend/lib/auth.ts` | NextAuth config |
| `frontend/hooks/use-events.ts` | SWR hooks for events |
| `frontend/hooks/use-allocation.ts` | SWR hooks for allocation |
| `frontend/vitest.config.ts` | Vitest config |
| `frontend/tests/lib/api.test.ts` | fetchAPI wrapper tests |
| `frontend/tests/components/login-form.test.tsx` | Login form tests |
| `frontend/tests/components/registration-form.test.tsx` | Registration form tests |
| `frontend/tests/components/config-form.test.tsx` | Config form tests |

---

## Task 1: Next.js Scaffold + Dependencies

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/.env.local.example`
- Create: `frontend/tsconfig.json`

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd squadsync
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir=false \
  --import-alias="@/*"
```

When prompted: accept all defaults.

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install \
  next-auth@beta \
  swr \
  react-hook-form \
  zod \
  @hookform/resolvers \
  react-qr-code \
  sonner \
  lucide-react \
  @radix-ui/react-dialog \
  @radix-ui/react-select \
  @radix-ui/react-slider \
  @radix-ui/react-label \
  @radix-ui/react-separator \
  @radix-ui/react-avatar \
  @radix-ui/react-badge \
  @radix-ui/react-progress \
  class-variance-authority \
  clsx \
  tailwind-merge \
  tailwindcss-animate

npm install -D \
  vitest \
  @vitejs/plugin-react \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jsdom \
  @types/node
```

- [ ] **Step 3: Initialize shadcn/ui**

```bash
npx shadcn@latest init
```

When prompted: style `default`, base color `slate`, CSS variables `yes`.

Then add components:

```bash
npx shadcn@latest add button input label card dialog select badge progress separator avatar toast
```

- [ ] **Step 4: Create `frontend/.env.local.example`**

```
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=change-me-to-a-long-random-string
NEXT_PUBLIC_API_URL=http://localhost:8000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

- [ ] **Step 5: Create `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 6: Create `frontend/tests/setup.ts`**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 7: Add test script to `frontend/package.json`**

In `scripts`, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd frontend
npm run dev
```

Expected: `Ready on http://localhost:3000`

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js 14 frontend scaffold + shadcn/ui + vitest"
```

---

## Task 2: API Client + NextAuth Config

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/auth.ts`
- Create: `frontend/app/api/auth/[...nextauth]/route.ts`
- Create: `frontend/tests/lib/api.test.ts`

- [ ] **Step 1: Write failing API client test**

Create `frontend/tests/lib/api.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mock
import { fetchAPI } from "@/lib/api";

describe("fetchAPI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends JSON request with base URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: "ok" }),
    });

    const result = await fetchAPI("/test");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/test"),
      expect.any(Object)
    );
    expect(result).toEqual({ data: "ok" });
  });

  it("includes Authorization header when token provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await fetchAPI("/test", { token: "my-jwt" });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe("Bearer my-jwt");
  });

  it("throws error with detail message on non-OK response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad request" }),
    });

    await expect(fetchAPI("/test")).rejects.toThrow("Bad request");
  });

  it("sends POST body as JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await fetchAPI("/test", { method: "POST", body: { name: "Alice" } });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.body).toBe(JSON.stringify({ name: "Alice" }));
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend
npm test
```

Expected: `Cannot find module '@/lib/api'`

- [ ] **Step 3: Create `frontend/lib/api.ts`**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface FetchOptions {
  method?: string;
  body?: unknown;
  token?: string;
  headers?: Record<string, string>;
}

export async function fetchAPI<T = unknown>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { method = "GET", body, token, headers: extraHeaders = {} } = options;

  const headers: Record<string, string> = {
    ...extraHeaders,
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npm test tests/lib/api.test.ts
```

Expected: All 4 tests `PASSED`.

- [ ] **Step 5: Create `frontend/lib/auth.ts`**

```typescript
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import { fetchAPI } from "@/lib/api";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          const res = await fetchAPI<{ access_token: string }>("/auth/login", {
            method: "POST",
            body: { email: credentials.email, password: credentials.password },
          });
          return { id: res.access_token, accessToken: res.access_token };
        } catch {
          return null;
        }
      },
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ account, user }) {
      if (account?.provider === "google") {
        try {
          const res = await fetchAPI<{ access_token: string }>("/auth/google", {
            method: "POST",
            body: { token: account.id_token },
          });
          (user as Record<string, unknown>).accessToken = res.access_token;
        } catch {
          return false;
        }
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as Record<string, unknown>).accessToken as string;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
});
```

- [ ] **Step 6: Create `frontend/app/api/auth/[...nextauth]/route.ts`**

```typescript
import { handlers } from "@/lib/auth";
export const { GET, POST } = handlers;
```

- [ ] **Step 7: Extend NextAuth types**

Create `frontend/types/next-auth.d.ts`:

```typescript
import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
  }
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/lib/ frontend/app/api/ frontend/types/ frontend/tests/lib/
git commit -m "feat: API client (fetchAPI wrapper) + NextAuth v5 config + tests"
```

---

## Task 3: Root Layout + Auth Pages

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/app/(auth)/login/page.tsx`
- Create: `frontend/app/(auth)/register/page.tsx`
- Create: `frontend/components/auth/login-form.tsx`
- Create: `frontend/components/auth/register-form.tsx`
- Create: `frontend/tests/components/login-form.test.tsx`

- [ ] **Step 1: Write failing login form test**

Create `frontend/tests/components/login-form.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { LoginForm } from "@/components/auth/login-form";

vi.mock("next-auth/react", () => ({
  signIn: vi.fn().mockResolvedValue({ ok: true }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("shows validation error when email is empty", async () => {
    render(<LoginForm />);
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });

  it("calls signIn with credentials on submit", async () => {
    const { signIn } = await import("next-auth/react");
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(signIn).toHaveBeenCalledWith("credentials", expect.objectContaining({
        email: "alice@test.com",
        password: "pass123",
      }));
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm test tests/components/login-form.test.tsx
```

Expected: `Cannot find module '@/components/auth/login-form'`

- [ ] **Step 3: Update `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { SessionProvider } from "next-auth/react";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SquadSync — Group Allocation Engine",
  description: "Intelligent team formation for hackathons, workshops, and events",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SessionProvider>
          {children}
          <Toaster richColors position="top-right" />
        </SessionProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Create `frontend/components/auth/login-form.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    const result = await signIn("credentials", { ...data, redirect: false });
    setLoading(false);
    if (result?.ok) {
      router.push("/dashboard");
    } else {
      toast.error("Invalid email or password");
    }
  };

  const handleGoogle = () => signIn("google", { callbackUrl: "/dashboard" });

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="you@example.com" {...register("email")} />
          {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" placeholder="••••••••" {...register("password")} />
          {errors.password && <p className="text-sm text-red-500">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs text-muted-foreground">
          <span className="bg-background px-2">or</span>
        </div>
      </div>
      <Button variant="outline" className="w-full" onClick={handleGoogle} type="button">
        Continue with Google
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/components/auth/register-form.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Invalid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type FormData = z.infer<typeof schema>;

export function RegisterForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await fetchAPI("/auth/register", { method: "POST", body: data });
      await signIn("credentials", { email: data.email, password: data.password, redirect: false });
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => signIn("google", { callbackUrl: "/dashboard" });

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="name">Name</Label>
          <Input id="name" placeholder="Your full name" {...register("name")} />
          {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="you@example.com" {...register("email")} />
          {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" placeholder="Min. 8 characters" {...register("password")} />
          {errors.password && <p className="text-sm text-red-500">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs text-muted-foreground">
          <span className="bg-background px-2">or</span>
        </div>
      </div>
      <Button variant="outline" className="w-full" onClick={handleGoogle} type="button">
        Continue with Google
      </Button>
    </div>
  );
}
```

- [ ] **Step 6: Create auth page files**

Create `frontend/app/(auth)/login/page.tsx`:

```typescript
import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">SquadSync</CardTitle>
          <CardDescription>Sign in to your organizer account</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
          <p className="mt-4 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link href="/register" className="text-primary font-medium hover:underline">
              Create one
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

Create `frontend/app/(auth)/register/page.tsx`:

```typescript
import Link from "next/link";
import { RegisterForm } from "@/components/auth/register-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function RegisterPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">SquadSync</CardTitle>
          <CardDescription>Create your organizer account</CardDescription>
        </CardHeader>
        <CardContent>
          <RegisterForm />
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
npm test tests/components/login-form.test.tsx
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/(auth)/ frontend/components/auth/ frontend/tests/components/login-form.test.tsx
git commit -m "feat: root layout + auth pages (login, register) + tests"
```

---

## Task 4: Dashboard Shell (Sidebar + Topbar + Layout)

**Files:**
- Create: `frontend/components/layout/sidebar.tsx`
- Create: `frontend/components/layout/topbar.tsx`
- Create: `frontend/app/(dashboard)/layout.tsx`

- [ ] **Step 1: Create `frontend/components/layout/sidebar.tsx`**

```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Calendar, Users, Zap, BarChart2, Download,
  Settings, ChevronLeft, ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const navItems = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "Events", href: "/dashboard/events", icon: Calendar },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r bg-white transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className={cn("flex items-center h-16 border-b px-4", collapsed ? "justify-center" : "justify-between")}>
        {!collapsed && (
          <span className="font-bold text-lg tracking-tight text-primary">SquadSync</span>
        )}
        <Button variant="ghost" size="icon" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 border-t bg-white flex justify-around py-2 z-50">
      {navItems.map(({ label, href, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-col items-center gap-0.5 text-xs",
              active ? "text-primary" : "text-slate-500"
            )}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Create `frontend/components/layout/topbar.tsx`**

```typescript
"use client";

import { useSession, signOut } from "next-auth/react";
import { Bell, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function Topbar() {
  const { data: session } = useSession();

  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6">
      <div className="md:hidden font-bold text-primary text-lg">SquadSync</div>
      <div className="flex-1" />
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Bell className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">
                  {session?.user?.name?.[0]?.toUpperCase() ?? "U"}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem className="text-sm text-muted-foreground" disabled>
              {session?.user?.email}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => signOut({ callbackUrl: "/login" })}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Add missing shadcn components**

```bash
cd frontend
npx shadcn@latest add dropdown-menu avatar
```

- [ ] **Step 4: Create `frontend/app/(dashboard)/layout.tsx`**

```typescript
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Sidebar, MobileNav } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect("/login");

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-auto p-6 pb-20 md:pb-6">
          {children}
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/ frontend/app/(dashboard)/layout.tsx
git commit -m "feat: dashboard shell (sidebar, topbar, layout with auth guard)"
```

---

## Task 5: SWR Hooks + Overview Page + Create Event Dialog

**Files:**
- Create: `frontend/hooks/use-events.ts`
- Create: `frontend/components/events/event-card.tsx`
- Create: `frontend/components/events/create-event-dialog.tsx`
- Create: `frontend/app/(dashboard)/page.tsx`

- [ ] **Step 1: Create `frontend/hooks/use-events.ts`**

```typescript
import useSWR, { mutate } from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";

export interface Event {
  id: string;
  title: string;
  description?: string;
  participant_limit?: number;
  team_count: number;
  status: string;
  registration_slug: string;
}

function useToken() {
  const { data: session } = useSession();
  return session?.accessToken;
}

export function useEvents() {
  const token = useToken();
  const { data, error, isLoading } = useSWR(
    token ? ["/api/v1/events", token] : null,
    ([path, t]) => fetchAPI<Event[]>(path, { token: t })
  );
  return { events: data ?? [], error, isLoading };
}

export function useEvent(eventId: string | null) {
  const token = useToken();
  const { data, error, isLoading } = useSWR(
    token && eventId ? [`/api/v1/events/${eventId}`, token] : null,
    ([path, t]) => fetchAPI<Event>(path, { token: t })
  );
  return { event: data, error, isLoading };
}

export async function createEvent(token: string, payload: Partial<Event>) {
  const result = await fetchAPI<Event>("/api/v1/events", {
    method: "POST",
    body: payload,
    token,
  });
  mutate(["/api/v1/events", token]);
  return result;
}
```

- [ ] **Step 2: Create `frontend/components/events/event-card.tsx`**

```typescript
import Link from "next/link";
import { Calendar, Users, ArrowRight } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Event } from "@/hooks/use-events";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  draft: "secondary",
  active: "default",
  allocated: "outline",
  archived: "destructive",
};

export function EventCard({ event }: { event: Event }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-base font-semibold line-clamp-1">{event.title}</CardTitle>
          <Badge variant={statusVariant[event.status] ?? "secondary"} className="ml-2 capitalize text-xs">
            {event.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {event.participant_limit ? `Max ${event.participant_limit}` : "No limit"}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {event.team_count} teams
          </span>
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild variant="ghost" size="sm" className="ml-auto">
          <Link href={`/dashboard/events/${event.id}`}>
            Manage <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
```

- [ ] **Step 3: Create `frontend/components/events/create-event-dialog.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { createEvent } from "@/hooks/use-events";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  team_count: z.coerce.number().int().min(2, "Minimum 2 teams"),
  participant_limit: z.coerce.number().int().min(1).optional().or(z.literal("")),
});

type FormData = z.infer<typeof schema>;

export function CreateEventDialog() {
  const { data: session } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { team_count: 5 },
  });

  const onSubmit = async (data: FormData) => {
    if (!session?.accessToken) return;
    setLoading(true);
    try {
      const event = await createEvent(session.accessToken, {
        ...data,
        participant_limit: data.participant_limit ? Number(data.participant_limit) : undefined,
      });
      setOpen(false);
      reset();
      router.push(`/dashboard/events/${event.id}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create event");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> New Event
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Event</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="title">Event Name</Label>
            <Input id="title" placeholder="Hackathon 2026" {...register("title")} />
            {errors.title && <p className="text-sm text-red-500">{errors.title.message}</p>}
          </div>
          <div className="space-y-1">
            <Label htmlFor="description">Description (optional)</Label>
            <Input id="description" placeholder="Brief description" {...register("description")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="team_count">Number of Teams</Label>
              <Input id="team_count" type="number" min={2} {...register("team_count")} />
              {errors.team_count && <p className="text-sm text-red-500">{errors.team_count.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="participant_limit">Max Participants</Label>
              <Input id="participant_limit" type="number" min={1} placeholder="No limit" {...register("participant_limit")} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating…" : "Create Event"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Create `frontend/app/(dashboard)/page.tsx`**

```typescript
"use client";

import { useEvents } from "@/hooks/use-events";
import { EventCard } from "@/components/events/event-card";
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { Skeleton } from "@/components/ui/skeleton";

export default function OverviewPage() {
  const { events, isLoading } = useEvents();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground text-sm">Manage your events and team allocations</p>
        </div>
        <CreateEventDialog />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-lg" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg font-medium">No events yet</p>
          <p className="text-sm mt-1">Create your first event to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map(event => <EventCard key={event.id} event={event} />)}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Add missing shadcn components**

```bash
npx shadcn@latest add skeleton
```

- [ ] **Step 6: Commit**

```bash
git add frontend/hooks/use-events.ts frontend/components/events/ frontend/app/(dashboard)/page.tsx
git commit -m "feat: overview page + event card + create event dialog + SWR hooks"
```

---

## Task 6: Attendees Page + QR Display

**Files:**
- Create: `frontend/components/attendees/attendees-table.tsx`
- Create: `frontend/components/attendees/qr-display.tsx`
- Create: `frontend/app/(dashboard)/events/[eventId]/attendees/page.tsx`
- Create: `frontend/app/(dashboard)/events/[eventId]/page.tsx`

- [ ] **Step 1: Create `frontend/components/attendees/qr-display.tsx`**

```typescript
"use client";

import { useRef } from "react";
import QRCode from "react-qr-code";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface QRDisplayProps {
  slug: string;
}

export function QRDisplay({ slug }: QRDisplayProps) {
  const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
  const url = `${baseUrl}/join/${slug}`;
  const qrRef = useRef<HTMLDivElement>(null);

  const downloadQR = () => {
    const svg = qrRef.current?.querySelector("svg");
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx?.drawImage(img, 0, 0);
      const a = document.createElement("a");
      a.download = `squadsync-qr-${slug}.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
    };
    img.src = `data:image/svg+xml;base64,${btoa(svgData)}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Registration QR Code</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div ref={qrRef} className="p-4 bg-white rounded-lg border">
          <QRCode value={url} size={160} />
        </div>
        <p className="text-xs text-muted-foreground text-center break-all">{url}</p>
        <Button variant="outline" size="sm" onClick={downloadQR}>
          <Download className="mr-2 h-3.5 w-3.5" /> Download PNG
        </Button>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create `frontend/components/attendees/attendees-table.tsx`**

```typescript
"use client";

import { useState } from "react";
import useSWR from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

interface Participant {
  id: string;
  name: string;
  email: string;
  role: string;
  skill_level: string;
  years_experience: number;
  composite_score?: number;
  registered_at: string;
}

const skillColor: Record<string, string> = {
  beginner: "bg-green-100 text-green-800",
  intermediate: "bg-blue-100 text-blue-800",
  advanced: "bg-purple-100 text-purple-800",
  professional: "bg-orange-100 text-orange-800",
};

export function AttendeesTable({ eventId }: { eventId: string }) {
  const { data: session } = useSession();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [skillFilter, setSkillFilter] = useState("all");

  const params = new URLSearchParams();
  if (roleFilter !== "all") params.set("role", roleFilter);
  if (skillFilter !== "all") params.set("skill", skillFilter);

  const { data: participants = [], isLoading } = useSWR(
    session?.accessToken ? [`/api/v1/events/${eventId}/participants`, params.toString(), session.accessToken] : null,
    ([path, q, token]) => fetchAPI<Participant[]>(`${path}?${q}`, { token })
  );

  const filtered = participants.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Search by name or email…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            {["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"]
              .map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={skillFilter} onValueChange={setSkillFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All levels" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All levels</SelectItem>
            {["beginner","intermediate","advanced","professional"]
              .map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                {["Name", "Email", "Role", "Skill", "Exp.", "Score"].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">No participants found</td></tr>
              ) : filtered.map(p => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{p.email}</td>
                  <td className="px-4 py-3 capitalize">{p.role}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${skillColor[p.skill_level]}`}>
                      {p.skill_level}
                    </span>
                  </td>
                  <td className="px-4 py-3">{p.years_experience}y</td>
                  <td className="px-4 py-3 font-mono">{p.composite_score?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">{filtered.length} participant{filtered.length !== 1 ? "s" : ""}</p>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/app/(dashboard)/events/[eventId]/page.tsx`**

```typescript
"use client";

import Link from "next/link";
import { useEvent } from "@/hooks/use-events";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Settings, Zap, ArrowRight } from "lucide-react";

export default function EventPage({ params }: { params: { eventId: string } }) {
  const { event, isLoading } = useEvent(params.eventId);
  if (isLoading) return <div className="animate-pulse space-y-4"><div className="h-8 bg-slate-200 rounded w-1/3" /></div>;
  if (!event) return <p className="text-muted-foreground">Event not found</p>;

  const quickActions = [
    { label: "Attendees", icon: Users, href: "attendees", description: "View participants & QR code" },
    { label: "Configure", icon: Settings, href: "configure", description: "Set allocation weights & rules" },
    { label: "Run Allocation", icon: Zap, href: "engine", description: "Generate balanced teams" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{event.title}</h1>
          {event.description && <p className="text-muted-foreground text-sm mt-1">{event.description}</p>}
        </div>
        <Badge className="capitalize">{event.status}</Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {quickActions.map(({ label, icon: Icon, href, description }) => (
          <Card key={href} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Icon className="h-4 w-4 text-primary" /> {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">{description}</p>
              <Button asChild variant="ghost" size="sm" className="p-0 h-auto">
                <Link href={`/dashboard/events/${params.eventId}/${href}`}>
                  Go <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/app/(dashboard)/events/[eventId]/attendees/page.tsx`**

```typescript
"use client";

import { useEvent } from "@/hooks/use-events";
import { AttendeesTable } from "@/components/attendees/attendees-table";
import { QRDisplay } from "@/components/attendees/qr-display";

export default function AttendeesPage({ params }: { params: { eventId: string } }) {
  const { event } = useEvent(params.eventId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Attendees</h1>
        <p className="text-sm text-muted-foreground">Manage participants and share the registration QR code</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <AttendeesTable eventId={params.eventId} />
        </div>
        <div>
          {event && <QRDisplay slug={event.registration_slug} />}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/attendees/ frontend/app/(dashboard)/events/
git commit -m "feat: event dashboard + attendees table + QR display"
```

---

## Task 7: Configure Page

**Files:**
- Create: `frontend/components/configure/config-form.tsx`
- Create: `frontend/app/(dashboard)/events/[eventId]/configure/page.tsx`
- Create: `frontend/tests/components/config-form.test.tsx`

- [ ] **Step 1: Write failing config form test**

Create `frontend/tests/components/config-form.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConfigForm } from "@/components/configure/config-form";

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { accessToken: "token" } }) }));
vi.mock("swr", () => ({
  default: () => ({ data: { weight_experience: 0.5, weight_skill: 0.5, role_constraints: {} }, isLoading: false }),
  mutate: vi.fn(),
}));

describe("ConfigForm", () => {
  it("renders weight sliders", () => {
    render(<ConfigForm eventId="event-123" />);
    expect(screen.getByText(/experience weight/i)).toBeInTheDocument();
    expect(screen.getByText(/skill weight/i)).toBeInTheDocument();
  });

  it("shows Add Constraint button", () => {
    render(<ConfigForm eventId="event-123" />);
    expect(screen.getByRole("button", { name: /add constraint/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm test tests/components/config-form.test.tsx
```

Expected: `Cannot find module '@/components/configure/config-form'`

- [ ] **Step 3: Create `frontend/hooks/use-allocation.ts`**

```typescript
import useSWR, { mutate } from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";

export interface AllocationConfig {
  id: string;
  event_id: string;
  weight_experience: number;
  weight_skill: number;
  role_constraints: Record<string, number>;
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  skill_level: string;
  composite_score?: number;
}

export interface Team {
  id: string;
  name: string;
  fairness_score?: number;
  skill_score?: number;
  role_balance_score?: number;
  members: TeamMember[];
}

export interface Allocation {
  id: string;
  event_id: string;
  snapshot_hash: string;
  status: string;
  constraint_warnings: Record<string, string[]>;
  teams: Team[];
}

function useToken() {
  const { data: session } = useSession();
  return session?.accessToken;
}

export function useAllocationConfig(eventId: string) {
  const token = useToken();
  const { data, isLoading } = useSWR(
    token ? [`/api/v1/events/${eventId}/config`, token] : null,
    ([path, t]) => fetchAPI<AllocationConfig>(path, { token: t })
  );
  return { config: data, isLoading };
}

export async function saveAllocationConfig(token: string, eventId: string, payload: Partial<AllocationConfig>) {
  const result = await fetchAPI<AllocationConfig>(`/api/v1/events/${eventId}/config`, {
    method: "PUT",
    body: payload,
    token,
  });
  mutate([`/api/v1/events/${eventId}/config`, token]);
  return result;
}

export async function runAllocation(token: string, eventId: string) {
  return fetchAPI<Allocation>(`/api/v1/events/${eventId}/allocate`, { method: "POST", token });
}

export async function publishAllocation(token: string, eventId: string, allocationId: string) {
  return fetchAPI(`/api/v1/events/${eventId}/allocations/${allocationId}/publish`, { method: "POST", token });
}
```

- [ ] **Step 4: Create `frontend/components/configure/config-form.tsx`**

```typescript
"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { useAllocationConfig, saveAllocationConfig } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const ROLES = ["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"];

interface Constraint { role: string; min: number; }

export function ConfigForm({ eventId }: { eventId: string }) {
  const { data: session } = useSession();
  const { config, isLoading } = useAllocationConfig(eventId);
  const [wExp, setWExp] = useState(0.5);
  const [constraints, setConstraints] = useState<Constraint[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (config) {
      setWExp(config.weight_experience);
      setConstraints(
        Object.entries(config.role_constraints).map(([role, min]) => ({ role, min: min as number }))
      );
    }
  }, [config]);

  const wSkill = Math.round((1 - wExp) * 100) / 100;

  const addConstraint = () => setConstraints(c => [...c, { role: "frontend", min: 1 }]);
  const removeConstraint = (i: number) => setConstraints(c => c.filter((_, idx) => idx !== i));
  const updateConstraint = (i: number, field: keyof Constraint, value: string | number) =>
    setConstraints(c => c.map((item, idx) => idx === i ? { ...item, [field]: value } : item));

  const handleSave = async () => {
    if (!session?.accessToken) return;
    setSaving(true);
    try {
      const role_constraints = Object.fromEntries(constraints.map(c => [c.role, c.min]));
      await saveAllocationConfig(session.accessToken, eventId, {
        weight_experience: wExp,
        weight_skill: wSkill,
        role_constraints,
      });
      toast.success("Configuration saved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className="animate-pulse h-64 bg-slate-100 rounded-lg" />;

  return (
    <div className="space-y-6 max-w-xl">
      <Card>
        <CardHeader><CardTitle className="text-base">Balancing Weights</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>Experience Weight</Label>
              <span className="text-sm font-mono">{(wExp * 100).toFixed(0)}%</span>
            </div>
            <Slider
              value={[wExp * 100]}
              min={10} max={90} step={5}
              onValueChange={([v]) => setWExp(v / 100)}
            />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>Skill Weight</Label>
              <span className="text-sm font-mono">{(wSkill * 100).toFixed(0)}%</span>
            </div>
            <Slider value={[wSkill * 100]} min={10} max={90} step={5} disabled className="opacity-60" />
            <p className="text-xs text-muted-foreground">Skill weight is automatically set to complement experience weight</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Role Constraints</CardTitle>
            <Button variant="outline" size="sm" onClick={addConstraint}>
              <Plus className="mr-1 h-3.5 w-3.5" /> Add Constraint
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {constraints.length === 0 ? (
            <p className="text-sm text-muted-foreground">No constraints — engine will balance freely</p>
          ) : constraints.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <Select value={c.role} onValueChange={v => updateConstraint(i, "role", v)}>
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground whitespace-nowrap">min</span>
              <Input
                type="number" min={1} max={10}
                value={c.min}
                onChange={e => updateConstraint(i, "min", Number(e.target.value))}
                className="w-16"
              />
              <Button variant="ghost" size="icon" onClick={() => removeConstraint(i)}>
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Saving…" : "Save Configuration"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/app/(dashboard)/events/[eventId]/configure/page.tsx`**

```typescript
import { ConfigForm } from "@/components/configure/config-form";

export default function ConfigurePage({ params }: { params: { eventId: string } }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Configure Allocation</h1>
        <p className="text-sm text-muted-foreground">Set balancing weights and role constraints</p>
      </div>
      <ConfigForm eventId={params.eventId} />
    </div>
  );
}
```

- [ ] **Step 6: Add Slider component**

```bash
npx shadcn@latest add slider
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
npm test tests/components/config-form.test.tsx
```

Expected: All 2 tests `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add frontend/hooks/use-allocation.ts frontend/components/configure/ frontend/app/(dashboard)/events/[eventId]/configure/
git commit -m "feat: allocation config form + configure page + SWR hooks"
```

---

## Task 8: Engine Page (Run + Results)

**Files:**
- Create: `frontend/components/engine/run-panel.tsx`
- Create: `frontend/components/engine/team-card.tsx`
- Create: `frontend/components/engine/results-grid.tsx`
- Create: `frontend/app/(dashboard)/events/[eventId]/engine/page.tsx`

- [ ] **Step 1: Create `frontend/components/engine/team-card.tsx`**

```typescript
import { Users, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Team } from "@/hooks/use-allocation";

const roleColor: Record<string, string> = {
  frontend: "bg-blue-100 text-blue-800",
  backend: "bg-purple-100 text-purple-800",
  fullstack: "bg-indigo-100 text-indigo-800",
  ai_ml: "bg-pink-100 text-pink-800",
  ux: "bg-yellow-100 text-yellow-800",
  devops: "bg-green-100 text-green-800",
  mobile: "bg-orange-100 text-orange-800",
  blockchain: "bg-teal-100 text-teal-800",
  product: "bg-cyan-100 text-cyan-800",
  marketing: "bg-red-100 text-red-800",
};

export function TeamCard({ team }: { team: Team }) {
  const roleCounts = team.members.reduce<Record<string, number>>((acc, m) => {
    acc[m.role] = (acc[m.role] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
          <div className="flex items-center gap-1 text-xs text-amber-600 font-medium">
            <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
            {team.fairness_score?.toFixed(0) ?? "—"}%
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          {team.members.length} member{team.members.length !== 1 ? "s" : ""}
        </div>

        <div className="flex flex-wrap gap-1">
          {Object.entries(roleCounts).map(([role, count]) => (
            <span
              key={role}
              className={`px-1.5 py-0.5 rounded text-xs font-medium capitalize ${roleColor[role] ?? "bg-slate-100 text-slate-800"}`}
            >
              {role} ×{count}
            </span>
          ))}
        </div>

        <div className="space-y-1">
          {[
            { label: "Skill", value: team.skill_score },
            { label: "Role Balance", value: team.role_balance_score },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground w-20">{label}</span>
              <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                <div
                  className="bg-primary rounded-full h-1.5 transition-all"
                  style={{ width: `${value ?? 0}%` }}
                />
              </div>
              <span className="font-mono w-8 text-right">{value?.toFixed(0) ?? "—"}</span>
            </div>
          ))}
        </div>

        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">View members</summary>
          <ul className="mt-2 space-y-1">
            {team.members.map(m => (
              <li key={m.id} className="flex justify-between">
                <span className="font-medium">{m.name}</span>
                <span className="text-muted-foreground capitalize">{m.role} · {m.skill_level}</span>
              </li>
            ))}
          </ul>
        </details>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create `frontend/components/engine/results-grid.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { AlertTriangle, Download, Link2, CheckCircle2 } from "lucide-react";
import { TeamCard } from "./team-card";
import { publishAllocation } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import type { Allocation } from "@/hooks/use-allocation";

interface ResultsGridProps {
  allocation: Allocation;
  eventId: string;
  onPublished: () => void;
}

export function ResultsGrid({ allocation, eventId, onPublished }: ResultsGridProps) {
  const { data: session } = useSession();
  const [publishing, setPublishing] = useState(false);
  const warningEntries = Object.entries(allocation.constraint_warnings);

  const handlePublish = async () => {
    if (!session?.accessToken) return;
    setPublishing(true);
    try {
      await publishAllocation(session.accessToken, eventId, allocation.id);
      toast.success("Teams published!");
      onPublished();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to publish");
    } finally {
      setPublishing(false);
    }
  };

  const handleCSV = () => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/allocations/${allocation.id}/export/csv`, "_blank");
  };

  const handleCopyLink = async () => {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/allocations/${allocation.id}/export/link`,
      { headers: { Authorization: `Bearer ${session?.accessToken}` } }
    );
    const { url } = await res.json();
    await navigator.clipboard.writeText(url);
    toast.success("Share link copied!");
  };

  return (
    <div className="space-y-4">
      {warningEntries.length > 0 && (
        <div className="flex items-start gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-800">Constraint warnings</p>
            <ul className="mt-1 space-y-0.5 text-amber-700">
              {warningEntries.map(([team, warnings]) =>
                warnings.map((w, i) => <li key={`${team}-${i}`}>{team}: {w}</li>)
              )}
            </ul>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {allocation.teams.map(team => <TeamCard key={team.id} team={team} />)}
      </div>

      <div className="flex flex-wrap gap-2 pt-2">
        {allocation.status === "draft" && (
          <Button onClick={handlePublish} disabled={publishing}>
            <CheckCircle2 className="mr-2 h-4 w-4" />
            {publishing ? "Publishing…" : "Publish Teams"}
          </Button>
        )}
        {allocation.status === "published" && (
          <>
            <Button variant="outline" onClick={handleCSV}>
              <Download className="mr-2 h-4 w-4" /> Export CSV
            </Button>
            <Button variant="outline" onClick={handleCopyLink}>
              <Link2 className="mr-2 h-4 w-4" /> Copy Share Link
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/engine/run-panel.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { Zap, Loader2 } from "lucide-react";
import { runAllocation } from "@/hooks/use-allocation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Allocation } from "@/hooks/use-allocation";

const PASSES = [
  "Pass 1 — Distributing anchors (Advanced / Professional)",
  "Pass 2 — Core balance pipeline (Intermediate)",
  "Pass 3 — Role constraint enforcement",
  "Pass 4 — Beginner fill",
];

interface RunPanelProps {
  eventId: string;
  participantCount: number;
  onComplete: (allocation: Allocation) => void;
}

export function RunPanel({ eventId, participantCount, onComplete }: RunPanelProps) {
  const { data: session } = useSession();
  const [running, setRunning] = useState(false);
  const [currentPass, setCurrentPass] = useState(-1);

  const handleRun = async () => {
    if (!session?.accessToken) return;
    setRunning(true);
    try {
      for (let i = 0; i < PASSES.length; i++) {
        setCurrentPass(i);
        await new Promise(r => setTimeout(r, 400));
      }
      const allocation = await runAllocation(session.accessToken, eventId);
      onComplete(allocation);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Allocation failed");
      setCurrentPass(-1);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle className="text-base">Allocation Engine</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {participantCount} participants ready for allocation.
          The engine will run 4 passes to distribute teams fairly.
        </p>

        {running && (
          <ul className="space-y-2">
            {PASSES.map((pass, i) => (
              <li key={i} className={`flex items-center gap-2 text-sm ${i <= currentPass ? "text-foreground" : "text-muted-foreground"}`}>
                {i < currentPass ? (
                  <span className="h-4 w-4 rounded-full bg-primary flex-shrink-0" />
                ) : i === currentPass ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                ) : (
                  <span className="h-4 w-4 rounded-full border border-slate-300 flex-shrink-0" />
                )}
                {pass}
              </li>
            ))}
          </ul>
        )}

        <Button onClick={handleRun} disabled={running || participantCount < 2} className="w-full">
          {running ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Running…</>
          ) : (
            <><Zap className="mr-2 h-4 w-4" /> Generate Teams</>
          )}
        </Button>
        {participantCount < 2 && (
          <p className="text-xs text-red-500">At least 2 participants required</p>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create `frontend/app/(dashboard)/events/[eventId]/engine/page.tsx`**

```typescript
"use client";

import { useState } from "react";
import useSWR from "swr";
import { useSession } from "next-auth/react";
import { fetchAPI } from "@/lib/api";
import { RunPanel } from "@/components/engine/run-panel";
import { ResultsGrid } from "@/components/engine/results-grid";
import type { Allocation } from "@/hooks/use-allocation";

export default function EnginePage({ params }: { params: { eventId: string } }) {
  const { data: session } = useSession();
  const [allocation, setAllocation] = useState<Allocation | null>(null);

  const { data: participants = [] } = useSWR(
    session?.accessToken ? [`/api/v1/events/${params.eventId}/participants`, session.accessToken] : null,
    ([path, token]) => fetchAPI<{ id: string }[]>(path, { token })
  );

  const handlePublished = () => {
    if (allocation) setAllocation({ ...allocation, status: "published" });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Allocation Engine</h1>
        <p className="text-sm text-muted-foreground">Generate balanced teams from registered participants</p>
      </div>

      {!allocation ? (
        <RunPanel
          eventId={params.eventId}
          participantCount={participants.length}
          onComplete={setAllocation}
        />
      ) : (
        <ResultsGrid
          allocation={allocation}
          eventId={params.eventId}
          onPublished={handlePublished}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/engine/ frontend/app/(dashboard)/events/[eventId]/engine/
git commit -m "feat: engine page — run panel, pass indicator, team results grid"
```

---

## Task 9: Public Registration Form

**Files:**
- Create: `frontend/components/registration/registration-form.tsx`
- Create: `frontend/app/join/[slug]/page.tsx`
- Create: `frontend/tests/components/registration-form.test.tsx`

- [ ] **Step 1: Write failing registration form test**

Create `frontend/tests/components/registration-form.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RegistrationForm } from "@/components/registration/registration-form";

vi.mock("@/lib/api", () => ({
  fetchAPI: vi.fn().mockResolvedValue({ name: "Alice", id: "p-1" }),
}));

const mockEvent = {
  id: "e-1",
  title: "Hackathon 2026",
  status: "active",
  description: "Build stuff",
};

describe("RegistrationForm", () => {
  it("renders all required fields", () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByText(/skill level/i)).toBeInTheDocument();
    expect(screen.getByText(/preferred role/i)).toBeInTheDocument();
  });

  it("shows validation error when name is empty", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it("shows confirmation after successful submit", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    await waitFor(() => {
      expect(screen.getByText(/you're registered/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm test tests/components/registration-form.test.tsx
```

Expected: `Cannot find module '@/components/registration/registration-form'`

- [ ] **Step 3: Create `frontend/components/registration/registration-form.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Invalid email"),
  phone: z.string().optional(),
  skill_level: z.enum(["beginner", "intermediate", "advanced", "professional"], {
    required_error: "Select your skill level",
  }),
  role: z.enum(["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"], {
    required_error: "Select your preferred role",
  }),
  years_experience: z.coerce.number().int().min(0),
});

type FormData = z.infer<typeof schema>;

interface EventInfo {
  id: string;
  title: string;
  status: string;
  description?: string;
}

export function RegistrationForm({ event, slug }: { event: EventInfo; slug: string }) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, control, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { years_experience: 0 },
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await fetchAPI(`/api/v1/events/${slug}/register`, { method: "POST", body: data });
      setSubmitted(true);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
        <CheckCircle2 className="h-16 w-16 text-green-500" />
        <h2 className="text-xl font-bold">You're registered!</h2>
        <p className="text-muted-foreground max-w-xs">
          Your registration for <strong>{event.title}</strong> has been confirmed. Teams will be announced soon.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="space-y-1">
        <Label htmlFor="name">Name</Label>
        <Input id="name" placeholder="Your full name" {...register("name")} />
        {errors.name && <p className="text-sm text-red-500">{errors.name.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="you@example.com" {...register("email")} />
        {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="phone">Phone (optional)</Label>
        <Input id="phone" type="tel" placeholder="+1 555 000 0000" {...register("phone")} />
      </div>

      <div className="space-y-1">
        <Label>Skill Level</Label>
        <Controller
          name="skill_level"
          control={control}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger><SelectValue placeholder="Select your level" /></SelectTrigger>
              <SelectContent>
                {["beginner","intermediate","advanced","professional"].map(s => (
                  <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.skill_level && <p className="text-sm text-red-500">{errors.skill_level.message}</p>}
      </div>

      <div className="space-y-1">
        <Label>Preferred Role</Label>
        <Controller
          name="role"
          control={control}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger><SelectValue placeholder="Select your role" /></SelectTrigger>
              <SelectContent>
                {["frontend","backend","fullstack","ai_ml","ux","devops","blockchain","mobile","product","marketing"].map(r => (
                  <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.role && <p className="text-sm text-red-500">{errors.role.message}</p>}
      </div>

      <div className="space-y-1">
        <Label htmlFor="years_experience">Years of Experience</Label>
        <Input id="years_experience" type="number" min={0} {...register("years_experience")} />
      </div>

      <Button type="submit" className="w-full" size="lg" disabled={loading}>
        {loading ? "Submitting…" : "Join Event"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 4: Create `frontend/app/join/[slug]/page.tsx`**

```typescript
import { fetchAPI } from "@/lib/api";
import { RegistrationForm } from "@/components/registration/registration-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface EventInfo {
  id: string;
  title: string;
  status: string;
  description?: string;
}

async function getEvent(slug: string): Promise<EventInfo | null> {
  try {
    return await fetchAPI<EventInfo>(`/api/v1/events/${slug}/info`);
  } catch {
    return null;
  }
}

export default async function JoinPage({ params }: { params: { slug: string } }) {
  const event = await getEvent(params.slug);

  if (!event) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-sm text-center">
          <CardContent className="pt-8 pb-8">
            <p className="text-lg font-semibold">Event not found</p>
            <p className="text-muted-foreground text-sm mt-1">This registration link may have expired or be invalid.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (event.status !== "active") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-sm text-center">
          <CardContent className="pt-8 pb-8">
            <p className="text-lg font-semibold">{event.title}</p>
            <p className="text-muted-foreground text-sm mt-1">
              Registration is currently {event.status === "allocated" ? "closed — teams have been formed" : "not open"}.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-start justify-center p-4 pt-8">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="text-2xl font-bold text-primary mb-1">SquadSync</div>
          <CardTitle>{event.title}</CardTitle>
          {event.description && <CardDescription>{event.description}</CardDescription>}
        </CardHeader>
        <CardContent>
          <RegistrationForm event={event} slug={params.slug} />
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npm test tests/components/registration-form.test.tsx
```

Expected: All 3 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/registration/ frontend/app/join/ frontend/tests/components/registration-form.test.tsx
git commit -m "feat: public registration form + join page + tests"
```

---

## Task 10: Public Results Page (Share Link Target)

**Files:**
- Create: `frontend/app/results/[allocationId]/page.tsx`

- [ ] **Step 1: Create `frontend/app/results/[allocationId]/page.tsx`**

```typescript
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Star } from "lucide-react";

interface TeamMember { id: string; name: string; role: string; skill_level: string; }
interface Team {
  id: string; name: string;
  fairness_score?: number;
  members: TeamMember[];
}
interface Allocation { id: string; status: string; teams: Team[]; }

async function getAllocation(id: string): Promise<Allocation | null> {
  try {
    return await fetchAPI<Allocation>(`/api/v1/allocations/${id}/teams`);
  } catch {
    return null;
  }
}

export default async function ResultsPage({ params }: { params: { allocationId: string } }) {
  const teams = await getAllocation(params.allocationId);

  if (!teams) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Results not found or not yet published.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-primary">SquadSync</h1>
          <p className="text-muted-foreground text-sm mt-1">Team Allocation Results</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(teams as unknown as Team[]).map(team => (
            <Card key={team.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">{team.name}</CardTitle>
                  {team.fairness_score && (
                    <span className="flex items-center gap-1 text-xs text-amber-600 font-medium">
                      <Star className="h-3 w-3 fill-amber-400 stroke-amber-400" />
                      {team.fairness_score.toFixed(0)}%
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {team.members.map(m => (
                    <li key={m.id} className="flex justify-between text-sm">
                      <span className="font-medium">{m.name}</span>
                      <span className="text-muted-foreground capitalize text-xs">{m.role}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/results/
git commit -m "feat: public results page for share links"
```

---

## Final Frontend Verification

- [ ] **Run the complete test suite**

```bash
cd frontend
npm test
```

Expected:
```
tests/lib/api.test.ts (4 tests) PASSED
tests/components/login-form.test.tsx (3 tests) PASSED
tests/components/registration-form.test.tsx (3 tests) PASSED
tests/components/config-form.test.tsx (2 tests) PASSED
```

- [ ] **Run the dev server and verify the golden path manually**

```bash
npm run dev
```

Check these routes work end-to-end:
1. `http://localhost:3000/register` — create account
2. `http://localhost:3000/login` — sign in
3. `http://localhost:3000/dashboard` — see overview
4. Create event → `http://localhost:3000/dashboard/events/{id}` — event page
5. Attendees tab → QR code visible + downloadable
6. Configure tab → save weights and a constraint
7. Engine tab → run allocation → see team cards → publish → export CSV
8. Open registration URL `http://localhost:3000/join/{slug}` — fill form → confirmation card

- [ ] **Run type check**

```bash
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Final commit**

```bash
git add frontend/
git commit -m "chore: frontend verification — all tests passing, type check clean"
```
