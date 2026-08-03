/**
 * Stitch before/after PNG pairs side-by-side for owner visual pack.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const sharp = require("sharp");

const root = path.resolve(process.cwd(), "e2e-artifacts/commercial-ux-slice-e-owner-visual");
const beforeDir = path.join(root, "before");
const afterDir = path.join(root, "after");
const pairsDir = path.join(root, "pairs");
fs.mkdirSync(pairsDir, { recursive: true });

const names = [
  "step1-desktop",
  "step1-mobile",
  "market-desktop",
  "materials-desktop",
  "review-desktop",
  "review-mobile",
];

for (const name of names) {
  const beforePath = path.join(beforeDir, `${name}.png`);
  const afterPath = path.join(afterDir, `${name}.png`);
  if (!fs.existsSync(beforePath) || !fs.existsSync(afterPath)) {
    console.warn("skip missing pair", name);
    continue;
  }
  const before = sharp(beforePath);
  const after = sharp(afterPath);
  const [bMeta, aMeta] = await Promise.all([before.metadata(), after.metadata()]);
  const height = Math.max(bMeta.height ?? 0, aMeta.height ?? 0);
  const bBuf = await before.resize({ height, fit: "contain", background: "#0a0a0a" }).png().toBuffer();
  const aBuf = await after.resize({ height, fit: "contain", background: "#0a0a0a" }).png().toBuffer();
  const bW = (await sharp(bBuf).metadata()).width ?? 0;
  const aW = (await sharp(aBuf).metadata()).width ?? 0;
  const gap = 8;
  const labelH = 36;
  const outW = bW + aW + gap;
  const outH = height + labelH;
  const svg = Buffer.from(
    `<svg width="${outW}" height="${labelH}"><text x="8" y="24" fill="#ccc" font-family="sans-serif" font-size="14">BEFORE (pre–Slice E)</text><text x="${bW + gap + 8}" y="24" fill="#ccc" font-family="sans-serif" font-size="14">AFTER (Slice E)</text></svg>`,
  );
  const outPath = path.join(pairsDir, `${name}-compare.png`);
  await sharp({
    create: {
      width: outW,
      height: outH,
      channels: 3,
      background: "#0a0a0a",
    },
  })
    .composite([
      { input: svg, top: 0, left: 0 },
      { input: bBuf, top: labelH, left: 0 },
      { input: aBuf, top: labelH, left: bW + gap },
    ])
    .png()
    .toFile(outPath);
  console.log("pair", outPath);
}
