import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

type BrandLogoSize = "header" | "compact";

type BrandLogoProps = {
  href?: string;
  className?: string;
  showWordmark?: boolean;
  size?: BrandLogoSize;
};

const sizeStyles: Record<
  BrandLogoSize,
  { image: string; imagePx: number; wordmark: string; gap: string }
> = {
  header: {
    image: "h-44 w-44 rounded-lg",
    imagePx: 176,
    wordmark: "text-4xl",
    gap: "gap-4",
  },
  compact: {
    image: "size-9 rounded-md",
    imagePx: 36,
    wordmark: "text-xl",
    gap: "gap-2.5",
  },
};

export function BrandLogo({
  href = "/",
  className,
  showWordmark = true,
  size = "header",
}: BrandLogoProps) {
  const styles = sizeStyles[size];

  return (
    <Link
      href={href}
      className={cn("inline-flex shrink-0 items-center", styles.gap, className)}
    >
      <Image
        src="/logo.svg"
        alt=""
        width={styles.imagePx}
        height={styles.imagePx}
        className={cn("shrink-0", styles.image)}
        priority
      />
      {showWordmark ? (
        <span
          className={cn(
            "font-heading font-bold tracking-tight text-foreground",
            styles.wordmark,
          )}
        >
          Hachapuri
        </span>
      ) : null}
      <span className="sr-only">Hachapuri home</span>
    </Link>
  );
}
