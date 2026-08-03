"use client";

import { useEffect, useState } from "react";
import {
  fetchVideoStudioCapabilities,
  type VideoStudioCapabilitiesDto,
} from "@/lib/api/endpoints/video-studio";

export function useVideoStudioCapabilities() {
  const [data, setData] = useState<VideoStudioCapabilitiesDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const caps = await fetchVideoStudioCapabilities();
        if (!cancelled) setData(caps);
      } catch {
        if (!cancelled) setError("capabilities_unavailable");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, error, loading };
}
