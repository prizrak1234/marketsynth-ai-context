"use client";

import type { ReactNode } from "react";

import type { MarketingSpecialistOutput } from "@/lib/api/types/marketing-specialist-outputs";

function ListSection({ title, items }: { title: string; items: unknown }) {
  if (!items) return null;
  const rows = Array.isArray(items) ? items : [items];
  if (!rows.length) return null;
  return (
    <div>
      <p className="font-medium text-foreground">{title}</p>
      <ul className="mt-0.5 list-inside list-disc text-muted-foreground">
        {rows.map((item, index) => (
          <li key={`${title}-${index}`}>
            {typeof item === "object" ? JSON.stringify(item) : String(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TextSection({ title, value }: { title: string; value: unknown }) {
  if (value == null || value === "") return null;
  return (
    <div>
      <p className="font-medium text-foreground">{title}</p>
      <p className="text-muted-foreground">{String(value)}</p>
    </div>
  );
}

function StructuredCard({
  output,
  children,
}: {
  output: MarketingSpecialistOutput;
  children: ReactNode;
}) {
  return (
    <div className="rounded border border-border/60 bg-muted/20 p-2 text-[10px]">
      <p className="font-medium">
        {output.title} · {output.output_type} · {output.status}
      </p>
      <div className="mt-2 flex flex-col gap-2">{children}</div>
    </div>
  );
}

function GenericStructuredCard({ output }: { output: MarketingSpecialistOutput }) {
  const data = output.structured_data ?? {};
  const keys = Object.keys(data).filter(
    (k) => !["llm_provider", "model", "mock"].includes(k),
  );
  return (
    <StructuredCard output={output}>
      {keys.length ? (
        keys.map((key) => (
          <ListSection key={key} title={key.replace(/_/g, " ")} items={data[key]} />
        ))
      ) : (
        <p className="text-muted-foreground">No structured data</p>
      )}
    </StructuredCard>
  );
}

export function V2SpecialistOutputCard({ output }: { output: MarketingSpecialistOutput }) {
  const data = output.structured_data ?? {};

  switch (output.output_type) {
    case "offer_strategy":
      return (
        <StructuredCard output={output}>
          <TextSection title="Core offer" value={data.core_offer} />
          <TextSection title="Value proposition" value={data.value_proposition} />
          <TextSection title="Unique mechanism" value={data.unique_mechanism} />
          <ListSection title="Offer variants" items={data.offer_variants} />
          <ListSection title="Pricing hypotheses" items={data.pricing_hypotheses} />
          <TextSection title="Risk reversal" value={data.risk_reversal} />
          <TextSection title="Positioning" value={data.positioning_statement} />
        </StructuredCard>
      );
    case "funnel_design":
      return (
        <StructuredCard output={output}>
          <ListSection title="Funnel stages" items={data.funnel_stages} />
          <ListSection title="Entry points" items={data.entry_points} />
          <TextSection title="Lead capture" value={data.lead_capture} />
          <ListSection title="Nurture sequence" items={data.nurture_sequence} />
          <ListSection title="Conversion events" items={data.conversion_events} />
          <ListSection title="Retention actions" items={data.retention_actions} />
        </StructuredCard>
      );
    case "lead_magnet":
      return (
        <StructuredCard output={output}>
          <TextSection title="Type" value={data.lead_magnet_type} />
          <ListSection title="Title variants" items={data.title_variants} />
          <TextSection title="Promise" value={data.promise} />
          <TextSection title="Delivery format" value={data.delivery_format} />
          <TextSection title="Qualification goal" value={data.qualification_goal} />
          <TextSection title="Follow-up" value={data.followup_recommendation} />
        </StructuredCard>
      );
    case "sales_copy":
      return (
        <StructuredCard output={output}>
          <TextSection title="Headline" value={data.headline} />
          <TextSection title="Offer" value={data.offer} />
          <ListSection title="Objections" items={data.objections} />
          <ListSection title="Benefits" items={data.benefits} />
          <TextSection title="CTA" value={data.cta} />
          <ListSection title="Sales sections" items={data.sales_sections} />
        </StructuredCard>
      );
    case "email_sequence":
      return (
        <StructuredCard output={output}>
          <ListSection title="Sequence steps" items={data.sequence_steps} />
          <ListSection title="Message goals" items={data.message_goals} />
          <TextSection title="CTA map" value={JSON.stringify(data.cta_map ?? {})} />
          <ListSection title="Trigger points" items={data.trigger_points} />
          <ListSection title="Follow-up rules" items={data.followup_rules} />
        </StructuredCard>
      );
    case "cro_recommendations":
      return (
        <StructuredCard output={output}>
          <ListSection title="Conversion bottlenecks" items={data.conversion_bottlenecks} />
          <ListSection title="Landing page" items={data.landing_page_recommendations} />
          <ListSection title="CTA improvements" items={data.cta_improvements} />
          <ListSection title="Trust elements" items={data.trust_elements} />
          <ListSection title="Form optimization" items={data.form_optimization} />
          <ListSection title="Test hypotheses" items={data.test_hypotheses} />
          <ListSection title="Priority actions" items={data.priority_actions} />
        </StructuredCard>
      );
    case "smm_strategy":
      return (
        <StructuredCard output={output}>
          <ListSection title="Platform focus" items={data.platform_focus} />
          <ListSection title="Content formats" items={data.content_formats} />
          <ListSection title="Posting frequency" items={data.posting_frequency} />
          <ListSection title="Engagement hooks" items={data.engagement_hooks} />
          <ListSection title="Community notes" items={data.community_management_notes} />
          <ListSection title="Social proof ideas" items={data.social_proof_ideas} />
          <ListSection title="Risks" items={data.risks} />
        </StructuredCard>
      );
    case "ad_creative_strategy":
      return (
        <StructuredCard output={output}>
          <ListSection title="Creative angles" items={data.creative_angles} />
          <ListSection title="Ad hooks" items={data.ad_hooks} />
          <ListSection title="Visual concepts" items={data.visual_concepts} />
          <ListSection title="Primary text variants" items={data.primary_text_variants} />
          <ListSection title="Headline variants" items={data.headline_variants} />
          <ListSection title="CTA variants" items={data.cta_variants} />
          <ListSection title="Testing matrix" items={data.testing_matrix} />
        </StructuredCard>
      );
    default:
      return <GenericStructuredCard output={output} />;
  }
}
