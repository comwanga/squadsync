"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Appearance</CardTitle>
          <CardDescription>Choose how SquadSync looks on your device</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <button
              onClick={() => setTheme("dark")}
              className={`flex-1 flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors ${
                theme === "dark"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <Moon className="h-5 w-5" />
              <span className="text-sm font-medium">Dark</span>
            </button>
            <button
              onClick={() => setTheme("light")}
              className={`flex-1 flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors ${
                theme === "light"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <Sun className="h-5 w-5" />
              <span className="text-sm font-medium">Light</span>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
