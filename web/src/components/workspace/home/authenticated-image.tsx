"use client";

import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/api/config";

type Props = {
  assetId: string;
  alt: string;
  className?: string;
  onMediaKind?: (kind: "image" | "video") => void;
};

/** Loads owner-scoped image with cookie credentials (cross-port API). */
export function AuthenticatedImage({ assetId, alt, className, onMediaKind }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    const url = `${getApiBaseUrl()}/generated-visual-assets/${assetId}/content`;
    (async () => {
      try {
        const res = await fetch(url, { credentials: "include", cache: "no-store" });
        if (!res.ok) throw new Error(`image_${res.status}`);
        const blob = await res.blob();
        if (cancelled) return;
        onMediaKind?.(blob.type.startsWith("video/") ? "video" : "image");
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetId]);

  if (error) {
    return (
      <p className="text-xs" style={{ color: "var(--ms-text-muted)" }} data-testid="home-image-error">
        {alt}
      </p>
    );
  }
  if (!src) {
    return (
      <div
        className="h-40 w-full max-w-md animate-pulse rounded-md"
        style={{ background: "var(--ms-bg-surface)" }}
        data-testid="home-image-loading"
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} className={className} data-testid="home-generated-image" />
  );
}
