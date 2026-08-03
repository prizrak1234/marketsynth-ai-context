import { ProductSkillsPanel } from "@/components/product-skills/product-skills-panel";
import { WorkspaceSectionShell } from "@/components/workspace/section-shell";

export default function Page() {
  return (
    <WorkspaceSectionShell title="Skills">
      <ProductSkillsPanel />
    </WorkspaceSectionShell>
  );
}
