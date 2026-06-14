import { test, expect, type Page } from "@playwright/test";

/** Assert a route resolves and isn't Next's 404 or a server error. */
async function expectRouteOk(page: Page, path: string) {
  const res = await page.goto(path, { waitUntil: "domcontentloaded" });
  expect(res, `no HTTP response for ${path}`).not.toBeNull();
  const status = res!.status();
  expect(status, `${path} returned HTTP ${status}`).toBeLessThan(400);
  await expect(
    page.getByText("This page could not be found"),
    `${path} rendered the Next 404 page`,
  ).toHaveCount(0);
}

/** Sign in by generating a fresh Nostr identity (the no-extension path). */
async function login(page: Page) {
  await page.goto("/login");
  await page.getByRole("button", { name: /Generate New Identity/i }).click();
  await page.getByRole("button", { name: /Sign In/i }).click();
  await page.waitForURL("**/dashboard", { timeout: 30_000 });
}

test.describe("public routes", () => {
  test("auth + public pages load without error", async ({ page }) => {
    await expectRouteOk(page, "/login");
    await expectRouteOk(page, "/register");
    // Unknown event/allocation should render a graceful not-found page (HTTP 200),
    // never a 404 route or a 500.
    await expectRouteOk(page, "/join/this-slug-does-not-exist");
    await expectRouteOk(
      page,
      "/results/00000000-0000-0000-0000-000000000000",
    );
  });
});

test.describe("authenticated routes", () => {
  test("every nav destination resolves", async ({ page }) => {
    await login(page);
    await expectRouteOk(page, "/dashboard");
    await expectRouteOk(page, "/dashboard/events"); // the route that 404'd
    await expectRouteOk(page, "/dashboard/settings");
  });

  test("an event's sub-routes all resolve", async ({ page }) => {
    await login(page);

    // Create an event through the UI; it redirects to /dashboard/events/{id}.
    await page.goto("/dashboard/events");
    await page.getByRole("button", { name: /New Event/i }).click();
    await page.getByLabel(/Event Name/i).fill("Smoke Test Event");
    await page.getByRole("button", { name: /^Create Event$/i }).click();
    await page.waitForURL(/\/dashboard\/events\/[0-9a-f-]+$/, { timeout: 30_000 });

    const eventId = page.url().split("/dashboard/events/")[1];
    expect(eventId, "expected an event id in the URL").toBeTruthy();

    for (const sub of ["", "/attendees", "/configure", "/engine"]) {
      await expectRouteOk(page, `/dashboard/events/${eventId}${sub}`);
    }
  });
});
