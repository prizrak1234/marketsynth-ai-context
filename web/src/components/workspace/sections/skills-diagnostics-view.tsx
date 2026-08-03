"use client";

import { useEffect, useState } from "react";
import { WorkspaceSectionShell } from "@/components/workspace/section-shell";
import {
  listCapabilityPacks,
  listSkillRouteMatrix,
  listSpecialistSkills,
  type CapabilityPackDto,
  type SpecialistSkillDto,
} from "@/lib/api/endpoints/knowledge-foundation";
import { useLocale } from "@/lib/i18n";

export function SkillsDiagnosticsView() {
  const { t } = useLocale();
  const [skills, setSkills] = useState<SpecialistSkillDto[]>([]);
  const [packs, setPacks] = useState<CapabilityPackDto[]>([]);
  const [routes, setRoutes] = useState<
    Array<{
      route_category: string;
      specialist_role: string | null;
      skill_code: string | null;
      notes: string;
    }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [execOff, setExecOff] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const [skillsRes, packsRes, routesRes] = await Promise.all([
          listSpecialistSkills(),
          listCapabilityPacks(),
          listSkillRouteMatrix(),
        ]);
        setSkills(skillsRes.skills);
        setExecOff(!skillsRes.execution_enabled && !skillsRes.prompts_exposed);
        setPacks(packsRes.packs);
        setRoutes(routesRes.mappings);
      } catch (err) {
        setError(err instanceof Error ? err.message : "load_failed");
      }
    })();
  }, []);

  return (
    <WorkspaceSectionShell
      title={t("skillsDiag.title")}
      description={t("skillsDiag.description")}
      testId="workspace-skills-diagnostics"
    >
      <div className="space-y-6 text-sm">
        <p style={{ color: "var(--ms-text-muted)" }} data-testid="skills-exec-flag">
          {execOff ? t("skillsDiag.noExecution") : t("skillsDiag.unexpectedExecution")}
        </p>
        {error ? (
          <p style={{ color: "var(--ms-danger, #b42318)" }}>{error}</p>
        ) : null}

        <section data-testid="skills-table">
          <h2 className="mb-2 text-base font-medium">{t("skillsDiag.skills")}</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <thead>
                <tr style={{ color: "var(--ms-text-muted)" }}>
                  <th className="border-b px-2 py-2 font-medium">Skill</th>
                  <th className="border-b px-2 py-2 font-medium">{t("common.version")}</th>
                  <th className="border-b px-2 py-2 font-medium">Specialist</th>
                  <th className="border-b px-2 py-2 font-medium">{t("common.status")}</th>
                  <th className="border-b px-2 py-2 font-medium">Knowledge</th>
                  <th className="border-b px-2 py-2 font-medium">Tools</th>
                  <th className="border-b px-2 py-2 font-medium">Gates</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((skill) => (
                  <tr key={skill.id} data-testid={`skill-row-${skill.code}`}>
                    <td className="border-b px-2 py-2">
                      <div>{skill.title}</div>
                      <div className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                        {skill.code}
                      </div>
                    </td>
                    <td className="border-b px-2 py-2">{skill.version}</td>
                    <td className="border-b px-2 py-2">{skill.specialist_roles.join(", ")}</td>
                    <td className="border-b px-2 py-2">{skill.status}</td>
                    <td className="border-b px-2 py-2">{skill.knowledge_scopes.join(", ")}</td>
                    <td className="border-b px-2 py-2">
                      {[...skill.required_tools, ...skill.optional_tools].join(", ") || "—"}
                    </td>
                    <td className="border-b px-2 py-2">{skill.quality_gates.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section data-testid="capability-packs">
          <h2 className="mb-2 text-base font-medium">{t("skillsDiag.packs")}</h2>
          <ul className="space-y-2">
            {packs.map((pack) => (
              <li key={pack.specialist_role} className="rounded border px-3 py-2"
                style={{ borderColor: "var(--ms-border-default)" }}>
                <strong>{pack.specialist_role}</strong> · v{pack.version}
                <div style={{ color: "var(--ms-text-secondary)" }}>
                  skills: {pack.allowed_skills.join(", ")}
                </div>
                <div style={{ color: "var(--ms-text-muted)" }}>
                  forbidden: {pack.forbidden_tools.join(", ")}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="skill-route-matrix">
          <h2 className="mb-2 text-base font-medium">{t("skillsDiag.routes")}</h2>
          <ul className="space-y-1" style={{ color: "var(--ms-text-secondary)" }}>
            {routes.map((row) => (
              <li key={row.route_category}>
                {row.route_category} → {row.specialist_role || "—"} → {row.skill_code || "path/clarify"}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </WorkspaceSectionShell>
  );
}
