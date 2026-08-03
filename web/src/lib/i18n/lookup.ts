/** Nested translation lookup with simple {param} interpolation. */

export type TranslationTree = { [key: string]: string | TranslationTree };

export function lookupTranslation(
  tree: TranslationTree,
  key: string,
  params?: Record<string, string | number>,
): string {
  const parts = key.split(".");
  let node: string | TranslationTree | undefined = tree;
  for (const part of parts) {
    if (node == null || typeof node === "string") {
      node = undefined;
      break;
    }
    node = node[part];
  }
  if (typeof node !== "string") {
    return key;
  }
  if (!params) return node;
  return node.replace(/\{(\w+)\}/g, (_, name: string) =>
    params[name] != null ? String(params[name]) : `{${name}}`,
  );
}
