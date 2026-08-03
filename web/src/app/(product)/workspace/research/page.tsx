import { redirect } from "next/navigation";

import { CANONICAL_COMMERCIAL_ROUTES } from "@/lib/routes/commercial-routes";

/** RUNTIME-01E — legacy alias frozen; canonical commercial home. */
export default function Page() {
  redirect(CANONICAL_COMMERCIAL_ROUTES.workspaceHome);
}
