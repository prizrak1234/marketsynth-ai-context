import type {
  BivCustomerResearchReport,
  BusinessIdeaValidationOutput,
} from "@/lib/api/types/business-idea-validation";

const SNAKE_CASE = /^[a-z][a-z0-9_]{2,}$/;
const EMPTY_MD = /\[[^\]]+\]\(\s*\)/g;

function verdictLabel(output: BusinessIdeaValidationOutput): string {
  const map: Record<string, string> = {
    proceed: "GO — запуск целесообразен",
    proceed_with_conditions: "CONDITIONAL GO — запуск с условиями",
    revise: "HOLD — требуется доработка идеи",
    reject: "NO GO — запуск не рекомендуется",
    insufficient_evidence: "PILOT ONLY — недостаточно доказательств для масштаба",
  };
  return map[output.verdict] ?? "HOLD";
}

function numberedSources(report: BivCustomerResearchReport): string[] {
  const seen = new Set<string>();
  const lines: string[] = [];
  let n = 1;
  for (const finding of report.confirmed_findings ?? []) {
    for (const src of finding.sources ?? []) {
      if (!src.url) continue;
      const key = src.url;
      if (seen.has(key)) continue;
      seen.add(key);
      const domain = src.domain ? ` (${src.domain})` : "";
      lines.push(`${n}. ${src.title}${domain} — ${src.url}`);
      n += 1;
    }
  }
  return lines;
}

export function buildCustomerReportExportText(args: {
  report: BivCustomerResearchReport;
  output: BusinessIdeaValidationOutput;
  projectName?: string;
  exportedAt?: Date;
}): string {
  const { report, output, projectName = "Marketsynth", exportedAt = new Date() } = args;
  const when = exportedAt.toISOString().replace("T", " ").slice(0, 16) + " UTC";
  const lines: string[] = [
    "MARKETSYNTH — КОММЕРЧЕСКОЕ ИССЛЕДОВАНИЕ",
    `Проект: ${projectName}`,
    `Дата экспорта: ${when}`,
    `Run ID: ${output.run_id ?? "—"}`,
    "",
    "=== ИТОГОВЫЙ СТАТУС ===",
    verdictLabel(output),
    report.executive_summary.status_line,
    `Общая уверенность: ${report.overall_confidence_percent}%`,
    `Покрытие: ${report.coverage.overall_percent}%`,
    "",
    "=== EXECUTIVE SUMMARY ===",
    report.executive_summary.status_line,
  ];

  if (report.executive_summary.primary_advantage) {
    lines.push("", "Главное преимущество:", report.executive_summary.primary_advantage);
  }
  if (report.executive_summary.primary_risk) {
    lines.push("", "Основной риск:", report.executive_summary.primary_risk);
  }

  if (report.confirmed_findings?.length) {
    lines.push("", "=== ЧТО ПОДТВЕРЖДЕНО ===");
    report.confirmed_findings.forEach((item, idx) => {
      lines.push(`${idx + 1}. ${item.headline}`);
      lines.push(`   ${item.explanation}`);
      for (const src of item.sources ?? []) {
        if (src.url) {
          lines.push(`   — ${src.title}: ${src.url}`);
        }
      }
    });
  }

  if (report.unconfirmed_topics?.length) {
    lines.push("", "=== ЧТО НЕ ПОДТВЕРЖДЕНО ===");
    for (const item of report.unconfirmed_topics) {
      lines.push(`• ${item.topic}`);
      lines.push(`  Причина: ${item.reason}`);
      lines.push(`  Итог: ${item.result_summary}`);
    }
  }

  const sv = report.structured_verdict;
  lines.push("", "=== ВЕРДИКТ ===", sv.recommendation);
  if (sv.risks?.length) {
    lines.push("", "Риски:", ...sv.risks.map((r) => `• ${r}`));
  }
  if (sv.verification_needed?.length) {
    lines.push("", "Что проверить дальше:", ...sv.verification_needed.map((q) => `• ${q}`));
  }

  const sources = numberedSources(report);
  if (sources.length) {
    lines.push("", "=== ИСТОЧНИКИ ===", ...sources);
  }

  return `${lines.join("\n").trim()}\n`;
}

export function validateCustomerReportExport(text: string): string[] {
  const violations: string[] = [];
  if (EMPTY_MD.test(text)) violations.push("empty_markdown_links");
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (SNAKE_CASE.test(t)) violations.push(`raw_code:${t}`);
  }
  if (text.trim().length < 80) violations.push("export_too_short");
  return violations;
}

export function downloadCustomerReportFile(args: {
  report: BivCustomerResearchReport;
  output: BusinessIdeaValidationOutput;
  projectName?: string;
}): void {
  const content = buildCustomerReportExportText(args);
  const violations = validateCustomerReportExport(content);
  if (violations.length > 0) {
    throw new Error("export_validation_failed");
  }
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const runToken = (args.output.run_id ?? "report").slice(0, 8);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `marketsynth-research-report-${runToken}.txt`;
  anchor.click();
  URL.revokeObjectURL(url);
}
