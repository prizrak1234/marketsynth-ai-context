/** Environment boundary for developer/internal commercial surfaces (no React imports). */

export function isDeveloperEnvironmentAllowed(
  nodeEnv: string | undefined = process.env.NODE_ENV,
): boolean {
  return nodeEnv !== "production";
}
