"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";

const ENTRANCE_KEY = "marketsynth.home.logo-entrance.v1";

type Props = {
  className?: string;
  priority?: boolean;
  /** One-shot fade + metallic gleam (once per tab session). */
  entrance?: boolean;
};

/**
 * Full master mark for Home hero.
 * Size via CSS clamp on `.ms-logo-hero--home` — aspect preserved, no crop.
 */
export function BrandLogoHero({ className, priority, entrance = false }: Props) {
  const [playEntrance, setPlayEntrance] = useState(false);

  useEffect(() => {
    if (!entrance || typeof window === "undefined") return;
    const reduce =
      window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
    if (reduce) return;
    try {
      if (window.sessionStorage.getItem(ENTRANCE_KEY) === "1") return;
      window.sessionStorage.setItem(ENTRANCE_KEY, "1");
      setPlayEntrance(true);
    } catch {
      setPlayEntrance(true);
    }
  }, [entrance]);

  return (
    <div
      className={`ms-logo-hero ${playEntrance ? "ms-logo-hero--enter" : ""} ${className ?? ""}`}
      data-testid="brand-logo-hero-wrap"
      data-entrance={playEntrance ? "1" : "0"}
    >
      <Image
        src={PRODUCT_BRAND.assets.master}
        alt="Marketsynth"
        width={1024}
        height={579}
        priority={priority}
        sizes="(max-width: 767px) 70vw, 38vw"
        className="ms-logo-hero__img"
        data-testid="brand-logo-hero"
      />
      {playEntrance ? (
        <span className="ms-logo-hero__gleam" aria-hidden data-testid="brand-logo-gleam" />
      ) : null}
    </div>
  );
}

type SymbolProps = {
  size?: number;
  className?: string;
  alt?: string;
};

/** Compact MS emblem for sidebar / chrome. Not the full master PNG. */
export function BrandLogoSymbol({ size = 28, className, alt }: SymbolProps) {
  const src = PRODUCT_BRAND.assets.symbol;
  if (!src) return null;
  return (
    <Image
      src={src}
      alt={alt ?? "Marketsynth"}
      width={size}
      height={size}
      className={className}
      style={{ width: size, height: size, objectFit: "contain" }}
      data-testid="brand-logo-symbol"
    />
  );
}

/** Symbol + wordmark for headers. */
export function BrandLogoMark({ size = 28 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2.5" data-testid="brand-logo-mark">
      <BrandLogoSymbol size={size} />
      <span
        className="text-sm font-semibold tracking-[0.08em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        {PRODUCT_BRAND.logoDisplayName}
      </span>
    </div>
  );
}
