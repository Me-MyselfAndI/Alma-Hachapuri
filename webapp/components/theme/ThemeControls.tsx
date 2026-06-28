"use client";

import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme/ThemeProvider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ThemeControlsProps = {
  className?: string;
};

export function ThemeControls({ className }: ThemeControlsProps) {
  const { mode, toggleMode, mounted } = useTheme();

  if (!mounted) {
    return <div className={cn("size-8", className)} aria-hidden />;
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className={className}
      onClick={toggleMode}
      title={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {mode === "dark" ? (
        <Sun className="size-4" aria-hidden />
      ) : (
        <Moon className="size-4" aria-hidden />
      )}
      <span className="sr-only">Toggle light or dark mode</span>
    </Button>
  );
}
