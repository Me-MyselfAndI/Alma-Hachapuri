"use client";

import { cn } from "@/lib/utils";

type FadeInProps = {
  children: React.ReactNode;
  className?: string;
  delay?: 0 | 1 | 2 | 3 | 4 | 5;
  variant?: "up" | "fade" | "scale";
};

const delayClass: Record<number, string> = {
  0: "",
  1: "stagger-1",
  2: "stagger-2",
  3: "stagger-3",
  4: "stagger-4",
  5: "stagger-5",
};

const variantClass = {
  up: "animate-fade-in-up opacity-0-start",
  fade: "animate-fade-in opacity-0-start",
  scale: "animate-scale-in opacity-0-start",
};

export function FadeIn({
  children,
  className,
  delay = 0,
  variant = "up",
}: FadeInProps) {
  return (
    <div
      className={cn(
        variantClass[variant],
        delay > 0 && delayClass[delay],
        className,
      )}
    >
      {children}
    </div>
  );
}
