export type BetaGuideStep = {
  key: string;
  label: string;
  hint: string | null;
};

export type BetaGuide = {
  current_phase: string;
  what_to_test: string[];
  expected_path: BetaGuideStep[];
  known_limitations: string[];
  feedback_instructions: string;
};

export type BetaAccess = {
  status: "pending" | "approved" | "blocked";
  gate_enabled: boolean;
  can_use_mvp: boolean;
  safe_message: string | null;
};
