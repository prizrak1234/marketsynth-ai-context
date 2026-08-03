export type ScenarioTemplate = {
  id: string;
  name: string;
  industry: string;
  goal: string;
  required_specialists: string[];
  default_plan_tasks: {
    specialist: string;
    objective: string;
    expected_output: string;
  }[];
  expected_artifacts: string[];
};
