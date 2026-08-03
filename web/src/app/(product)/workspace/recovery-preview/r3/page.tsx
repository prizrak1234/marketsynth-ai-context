import { redirect } from "next/navigation";

/** Recovery preview closed — canonical product is /workspace only. */
export default function RecoveryPreviewR3Page() {
  redirect("/workspace");
}
