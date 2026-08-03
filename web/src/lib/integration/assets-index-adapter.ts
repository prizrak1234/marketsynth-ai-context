/** Assets index — content assets + generated visuals (H2.6A). */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { listGeneratedVisualAssets } from "@/lib/api/endpoints/generated-visual-assets";
import { apiJson } from "@/lib/api/client";
import { getApiBaseUrl } from "@/lib/api/config";
import { getIntegrationMode } from "@/lib/integration/mode";

export type AssetIndexItem = {
  id: string;
  projectId: string;
  projectName: string;
  title: string;
  status: string;
  href: string;
  kind?: "content" | "generated_visual";
  previewUrl?: string | null;
  generationMode?: "real" | "mock" | null;
  provider?: string | null;
  assetType?: string | null;
};

export type AssetIndexResult = {
  state: "success" | "empty" | "error" | "unauthorized" | "mock_notice" | "unavailable";
  items: AssetIndexItem[];
  message: string | null;
};

type ContentAssetListDto = {
  id: string;
  title?: string | null;
  name?: string | null;
  status?: string | null;
  lifecycle_status?: string | null;
};

export async function loadAssetsIndex(): Promise<AssetIndexResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message: "Mock-режим: активы не подставляются из фикстур.",
    };
  }
  try {
    const items: AssetIndexItem[] = [];
    let listSupported = false;

    try {
      const visuals = await listGeneratedVisualAssets();
      listSupported = true;
      for (const v of visuals) {
        items.push({
          id: v.id,
          projectId: "",
          projectName:
            v.generation_mode === "mock" ? "Diagnostic (mock)" : "Generated",
          title: v.prompt_summary || `Image ${v.id.slice(0, 8)}`,
          status: v.status,
          href: `${getApiBaseUrl()}/generated-visual-assets/${v.id}/content`,
          kind: "generated_visual",
          previewUrl: `${getApiBaseUrl()}/generated-visual-assets/${v.id}/content`,
          generationMode: v.generation_mode,
          provider: v.provider,
          assetType: v.asset_type,
        });
      }
    } catch {
      /* generated visuals may be unavailable */
    }

    const projects = await fetchProjects();
    for (const p of projects) {
      try {
        const list = await apiJson<ContentAssetListDto[]>(
          `/projects/${p.id}/content-assets`,
        );
        listSupported = true;
        for (const a of list) {
          items.push({
            id: a.id,
            projectId: p.id,
            projectName: p.name,
            title: a.title || a.name || a.id.slice(0, 8),
            status: String(a.lifecycle_status || a.status || "—"),
            href: `/workspace/assets`,
            kind: "content",
          });
        }
      } catch {
        /* list may 404 — treat as unsupported for that project */
      }
    }
    if (!listSupported && items.length === 0) {
      return {
        state: "unavailable",
        items: [],
        message:
          "Активы появятся после создания контента, креативов, документов или публикационных материалов.",
      };
    }
    if (!items.length) {
      return {
        state: "empty",
        items: [],
        message:
          "Активы появятся после создания контента, креативов, документов или публикационных материалов.",
      };
    }
    return { state: "success", items, message: null };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (/401|403|unauthorized/i.test(msg)) {
      return { state: "unauthorized", items: [], message: "Нет доступа к активам." };
    }
    return {
      state: "unavailable",
      items: [],
      message:
        "Активы появятся после создания контента, креативов, документов или публикационных материалов.",
    };
  }
}
