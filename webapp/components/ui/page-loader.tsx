import { cn } from "@/lib/utils";

type PageLoaderProps = {
  label?: string;
  className?: string;
  fullScreen?: boolean;
};

export function PageLoader({
  label = "Loading…",
  className,
  fullScreen = false,
}: PageLoaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4",
        fullScreen ? "min-h-screen bg-background" : "min-h-[50vh]",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <div className="relative size-14">
        <div
          className="absolute inset-0 animate-gradient-spin rounded-full bg-gradient-brand p-[3px]"
          aria-hidden
        >
          <div className="size-full rounded-full bg-background" />
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
