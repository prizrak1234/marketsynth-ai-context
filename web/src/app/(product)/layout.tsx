import type { Metadata } from "next";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";

export const metadata: Metadata = {
  title: `${PRODUCT_BRAND.displayName} — Рабочее пространство`,
  description: PRODUCT_BRAND.positioning,
  icons: {
    icon: [
      { url: "/brand/marketsynth-favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/brand/marketsynth-favicon.ico" },
    ],
    apple: [{ url: "/brand/marketsynth-apple-touch-icon.png", sizes: "180x180" }],
  },
};

/**
 * Product Alpha workspace route group.
 * Independent of frozen Landing (`/`) and legacy internal AppShell.
 */
export default function ProductWorkspaceLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
