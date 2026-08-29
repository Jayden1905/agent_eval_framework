import { expect, test } from "@playwright/test";

test("the evaluation campus is usable without page-level overflow", async ({ page }, testInfo) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Put your agent to work/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Start evaluation/i })).toBeVisible();
  await expect(page.locator(".question-office")).toHaveCount(5);
  await expect(page.locator(".question-office.activity-typing")).toHaveCount(2);
  await expect(page.locator(".question-office.activity-pacing")).toHaveCount(2);
  await expect(page.locator(".question-office.activity-training")).toHaveCount(1);
  await expect(page.getByLabel(/Question 1 office: Queued/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /Question 1, run 1/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Question 5, run 3/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Question \d, run \d/i })).toHaveCount(15);

  const officeTab = page.getByRole("tab", { name: "Office floor" });
  await officeTab.focus();
  await officeTab.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Results grid" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tabpanel", { name: "Results grid" })).toBeVisible();
  await page.getByRole("tab", { name: "Results grid" }).press("ArrowLeft");
  await expect(officeTab).toHaveAttribute("aria-selected", "true");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);

  await page.getByRole("button", { name: /Question 3, run 2/i }).click();
  await expect(page.getByLabel("Selected sandbox details")).toContainText("Q3 / RUN 2");
  await expect(page.getByLabel("Selected sandbox details")).toContainText("How many islands");
  if (testInfo.project.name.startsWith("phone-") || testInfo.project.name === "tablet") {
    await expect(page.getByLabel("Selected sandbox details")).toBeInViewport();
    await expect(page.getByLabel("Selected sandbox details")).toBeFocused();
  }
});

test("dummy playback reaches an inspectable scorecard", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Playback flow is covered once at desktop size.");
  await page.goto("/");

  await page.getByRole("button", { name: /Start evaluation/i }).click();
  await expect(page.getByText("Evaluation in progress")).toBeVisible();
  await expect(page.locator(".question-office.office-running")).toHaveCount(5);
  await expect(page.locator(".question-office.office-running .agent-stage")).toHaveCount(5);
  await expect(page.locator(".question-office.office-running .spawn-scan")).toHaveCount(5);
  await page.getByRole("button", { name: /Fast-forward results/i }).click();

  await expect(page.getByRole("heading", { name: "4/5 questions passed" })).toBeVisible();
  await expect(page.getByText("80%")).toBeVisible();
  await expect(page.getByRole("table", { name: "Evaluation result grid" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "0.67" })).toBeVisible();

  await page.getByRole("tab", { name: "Office floor" }).click();
  await expect(page.locator(".question-office")).toHaveCount(5);
  await expect(page.locator(".question-office.office-fail")).toHaveCount(2);
  await expect(page.locator(".question-office.office-fail .anger-steam")).toHaveCount(2);
  await expect(page.locator(".question-office .result-bubble")).toHaveCount(5);
});

test("reduced motion preserves all meaningful state", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "phone-390", "Reduced-motion behavior is covered once on mobile.");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: /Start evaluation/i }).click();

  await expect(page.getByRole("button", { name: /Fast-forward results/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Question \d, run \d: Running/i }).first()).toBeVisible();
  await expect(page.getByLabel("Status legend")).toBeAttached();
});

test("a completed zero score remains visible and inspectable", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "Zero-score rendering is covered once at desktop size.");
  await page.goto("/");

  await page.getByRole("button", { name: "wrong" }).click();
  await page.getByRole("button", { name: /Start evaluation/i }).click();
  await page.getByRole("button", { name: /Fast-forward results/i }).click();

  const zeroScoreCell = page.getByRole("cell").filter({ has: page.getByRole("button", { name: /question 5, run 3: Failed, score 0\.00/i }) });
  await expect(zeroScoreCell).toContainText("0.00");
  await zeroScoreCell.getByRole("button").click();
  await expect(page.getByLabel("Selected sandbox details")).toContainText("0.00");
});
