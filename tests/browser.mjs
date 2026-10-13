// Browser acceptance uses a synthetic host; never capture a real desktop here.
import { chromium, firefox, webkit } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import assert from "node:assert/strict";
import { once } from "node:events";
const python = process.env.PYTHON || "python";
const root = process.cwd(),
  temp = await mkdtemp(path.join(tmpdir(), "beacn-view-qa-"));
const tokenFile = path.join(temp, "test.token");
async function command(args) {
  const p = spawn(python, ["-m", "beacn_view.cli", ...args], {
    stdio: "ignore",
  });
  const [code] = await once(p, "exit");
  assert.equal(code, 0);
}
await command(["init", "--token-file", tokenFile]);
const token = (await readFile(tokenFile, "utf8")).trim();
const port = process.env.BEACN_TEST_PORT || "18741",
  url = `http://127.0.0.1:${port}`;
const host = spawn(
  python,
  [
    "-m",
    "beacn_view.cli",
    "serve",
    "--demo",
    "--port",
    port,
    "--token-file",
    tokenFile,
  ],
  { stdio: "ignore" },
);
const results = [];
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(url)).ok) break;
    } catch {}
    await new Promise((r) => setTimeout(r, 100));
    if (i === 99) throw Error("Host startup failed");
  }
  await mkdir(path.join(root, "qa"), { recursive: true });
  for (const [name, engine] of Object.entries({ chromium, firefox, webkit })) {
    const browser = await engine.launch({ headless: true });
    try {
      for (const [label, viewport] of Object.entries({
        desktop: { width: 1440, height: 1000 },
        mobile: { width: 390, height: 844 },
      })) {
        const context = await browser.newContext({
          viewport,
          reducedMotion: "reduce",
          acceptDownloads: true,
        });
        const page = await context.newPage();
        const errors = [];
        page.on("pageerror", (err) => errors.push(err.message));
        await page.goto(url);
        await page.getByLabel("Host access token").fill("invalid");
        await page.getByRole("button", { name: "Connect to screen" }).click();
        await page.getByRole("alert").filter({ hasText: "rejected" }).waitFor();
        await page.getByLabel("Host access token").fill(token);
        await page.getByRole("button", { name: "Connect to screen" }).click();
        await page.locator("#frame:not([hidden])").waitFor();
        await page.getByRole("button", { name: "Pause", exact: true }).click();
        assert.equal(await page.locator("#token").inputValue(), "");
        assert.equal(
          await page.evaluate(
            () => localStorage.length + sessionStorage.length,
          ),
          0,
        );
        assert.deepEqual(await context.cookies(), []);
        if (label === "mobile")
          await page.getByText("View settings", { exact: true }).click();
        await page.getByLabel("Refresh", { exact: true }).selectOption("0");
        await page.getByRole("button", { name: "Resume", exact: true }).click();
        await page
          .getByRole("status")
          .filter({ hasText: "Manual capture" })
          .waitFor();
        await page.getByLabel("Zoom", { exact: true }).selectOption("1.5");
        await page.getByLabel("Zoom", { exact: true }).selectOption("fit");
        await page.getByText("Crop a region", { exact: true }).click();
        await page.getByLabel("Width", { exact: true }).fill("800");
        await page.getByLabel("Height", { exact: true }).fill("600");
        await page.getByRole("button", { name: "Apply crop" }).click();
        await page
          .locator("#frame-info")
          .filter({ hasText: "800 × 600" })
          .waitFor();
        const download = page.waitForEvent("download");
        await page.getByRole("button", { name: "Save JPEG" }).click();
        assert.match(
          (await download).suggestedFilename(),
          /^beacn-view-.*\.jpg$/,
        );
        for (const field of ["Width", "Height"])
          await page.getByLabel(field, { exact: true }).fill("0");
        await page.getByRole("button", { name: "Apply crop" }).click();
        await page
          .locator("#frame-info")
          .filter({ hasText: "1600 × 900" })
          .waitFor();
        await page.getByText("Crop a region", { exact: true }).click();
        if (label === "mobile")
          await page.getByText("View settings", { exact: true }).click();
        const axe = await new AxeBuilder({ page }).analyze();
        assert.equal(
          axe.violations.length,
          0,
          JSON.stringify(
            axe.violations.map((v) => ({
              id: v.id,
              nodes: v.nodes.map((n) => n.target),
            })),
          ),
        );
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        );
        assert.equal(overflow, false);
        assert.deepEqual(errors, []);
        await page.screenshot({
          path: path.join(root, "qa", `${name}-${label}.png`),
          fullPage: true,
        });
        if (name === "chromium" && label === "desktop")
          await page.screenshot({
            path: path.join(root, "docs", "viewer-demo.png"),
            fullPage: true,
          });
        await page
          .getByRole("button", { name: "Disconnect & clear screen" })
          .click();
        assert.equal(await page.locator("#frame").isVisible(), false);
        assert.equal(await page.locator("#frame").getAttribute("src"), null);
        // A late frame must not reappear after disconnect.
        await page.getByLabel("Host access token").fill(token);
        await page.getByRole("button", { name: "Connect to screen" }).click();
        await page.locator("#frame:not([hidden])").waitFor();
        await page.route("**/api/frame?**", async (route) => {
          await new Promise((r) => setTimeout(r, 500));
          await route.continue().catch(() => {});
        });
        await page.getByRole("button", { name: "Capture now" }).click();
        await page
          .getByRole("button", { name: "Disconnect & clear screen" })
          .click();
        await page.waitForTimeout(650);
        assert.equal(await page.locator("#frame").isVisible(), false);
        results.push({
          browser: name,
          viewport: label,
          passed: true,
          axeViolations: 0,
          consoleErrors: 0,
        });
        await context.close();
      }
    } finally {
      await browser.close();
    }
  }
  await writeFile(
    path.join(root, "qa", "browser-results.json"),
    JSON.stringify(results, null, 2),
  );
  console.log(JSON.stringify(results));
} finally {
  host.kill();
  await once(host, "exit").catch(() => {});
}
