// @ts-check
import { test, expect } from '@playwright/test'

/**
 * E2E suite for the Vinci Automation production deployment.
 *
 * Selectors were taken from the repo source (frontend/src):
 *  - Login:        .auth-form input[type=email|password], button.auth-submit,
 *                  error surfaced as .auth-error[role=alert]  (LoginPage.jsx)
 *  - Guards:       full-screen loader .auth-loader while the session/profile
 *                  resolves; unauthenticated users are redirected to /login
 *                  (guards.jsx)
 *  - Sidebar nav:  aside.sidebar a.nav-item with labels "Schedule",
 *                  "Lesson Dashboard", "Finances" (Admin only), "Urgent News"
 *                  (Sidebar.jsx)
 *  - Lesson Dashboard (/lessons):
 *                  header.topbar, stats bar .ld-stats > .ld-stat with
 *                  .ld-stat__count / .ld-stat__label ("Needs Action",
 *                  "Urgent (≤7 days)", "Unassigned / Offer Sent",
 *                  "Pending Approvals" — the "Has Acceptance" card), and the
 *                  conditional banner .ld-pending-banner shown only when
 *                  stats.hasAcceptance > 0 (LessonDashboardPage.jsx)
 */

const EMAIL = process.env.E2E_EMAIL || 'hansenyg@vinciai.academy'
const PASSWORD = process.env.E2E_PASSWORD || 'VinciBeta2026!'

/** Sign in via the real login form and wait for the app shell. */
async function login(page) {
  await page.goto('/login')
  await expect(page.locator('.auth-form')).toBeVisible()
  await page.locator('.auth-form input[type="email"]').fill(EMAIL)
  await page.locator('.auth-form input[type="password"]').fill(PASSWORD)
  await page.locator('button.auth-submit').click()
  // Successful login lands on / (index) which redirects to /schedule.
  await page.waitForURL(/\/schedule/, { timeout: 90_000 })
  // Wait until the auth/profile loader has fully resolved.
  await expect(page.locator('.auth-loader')).toHaveCount(0, { timeout: 90_000 })
  await expect(page.locator('aside.sidebar')).toBeVisible()
}

test.describe('1. Authentication Flow', () => {
  test('valid credentials sign in and land on the dashboard', async ({ page }) => {
    await page.goto('/')
    // Unauthenticated users are bounced to /login by RequireAuth.
    await page.waitForURL(/\/login/)
    await expect(page.locator('.auth-card .auth-title')).toHaveText('Sign in')

    await page.locator('.auth-form input[type="email"]').fill(EMAIL)
    await page.locator('.auth-form input[type="password"]').fill(PASSWORD)
    await page.locator('button.auth-submit').click()

    await page.waitForURL(/\/schedule/, { timeout: 90_000 })
    await expect(page.locator('aside.sidebar')).toBeVisible()
    await expect(page.locator('header.topbar')).toContainText('Schedule')
  })

  test('invalid credentials show an error state and stay on /login', async ({ page }) => {
    await page.goto('/login')
    await page.locator('.auth-form input[type="email"]').fill(EMAIL)
    await page.locator('.auth-form input[type="password"]').fill('definitely-wrong-password-123')
    await page.locator('button.auth-submit').click()

    const error = page.locator('.auth-error[role="alert"]')
    await expect(error).toBeVisible({ timeout: 60_000 })
    await expect(error).not.toBeEmpty()
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe('2. Session Persistence (Issue 1 regression)', () => {
  test('session survives window blur/focus and a full page reload', async ({ page }) => {
    await login(page)

    // Simulate the window losing and regaining focus (original Issue 1 trigger).
    await page.evaluate(() => {
      window.dispatchEvent(new Event('blur'))
      document.dispatchEvent(new Event('visibilitychange'))
      window.dispatchEvent(new Event('focus'))
    })
    // Give the app a moment to react; it must not log us out.
    await page.waitForTimeout(3_000)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('aside.sidebar')).toBeVisible()

    // Full reload — the persisted Supabase session must be restored.
    await page.reload()
    await page.waitForLoadState('domcontentloaded')
    // The loader may appear while the session resolves, but must settle.
    await expect(page.locator('.auth-loader')).toHaveCount(0, { timeout: 90_000 })
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('aside.sidebar')).toBeVisible()
    await expect(page.locator('header.topbar')).toBeVisible()
  })
})

test.describe('3. Lesson Dashboard UI (Issue 3 verification)', () => {
  test('stats cards render, including the "Pending Approvals" card', async ({ page }) => {
    await login(page)

    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)
    await expect(page.locator('header.topbar')).toContainText('Lesson Dashboard')

    // Stats bar with all four cards.
    const stats = page.locator('.ld-stats .ld-stat')
    await expect(stats).toHaveCount(4, { timeout: 60_000 })
    await expect(page.locator('.ld-stat__label', { hasText: 'Needs Action' })).toBeVisible()
    await expect(page.locator('.ld-stat__label', { hasText: 'Urgent (≤7 days)' })).toBeVisible()
    await expect(page.locator('.ld-stat__label', { hasText: 'Unassigned / Offer Sent' })).toBeVisible()

    // The "Has Acceptance" card is labelled "Pending Approvals" and is clickable.
    const pendingCard = page.locator('.ld-stat.ld-stat--action', { hasText: 'Pending Approvals' })
    await expect(pendingCard).toBeVisible()
    const pendingCount = Number(await pendingCard.locator('.ld-stat__count').innerText())
    console.log(`[info] Pending Approvals count from live DB: ${pendingCount}`)

    // The .ld-pending-banner is only rendered when hasAcceptance > 0,
    // so handle a zero-count live database gracefully.
    const banner = page.locator('.ld-pending-banner')
    if (pendingCount > 0) {
      await expect(banner).toBeVisible()
      await expect(banner).toContainText('awaiting approval')
      await expect(banner.locator('.ld-pending-banner__btn')).toHaveText('Review now')
      console.log('[info] Pending Approvals banner is visible, as expected.')
    } else {
      await expect(banner).toHaveCount(0)
      console.log('[info] Live DB has 0 pending approvals — banner correctly hidden.')
    }

    // Clicking the card applies the hasacceptance filter without errors.
    await pendingCard.click()
    await expect(page.locator('.ld-stats')).toBeVisible()
  })
})

test.describe('4. Basic Navigation', () => {
  test('sidebar routing works and headers update, no 404s', async ({ page }) => {
    const notFound = []
    page.on('response', (res) => {
      if (res.status() === 404 && res.url().startsWith(page.context()._options.baseURL || '')) {
        notFound.push(res.url())
      }
    })

    await login(page)

    const nav = page.locator('aside.sidebar')

    // Schedule
    await nav.locator('a.nav-item', { hasText: 'Schedule' }).click()
    await page.waitForURL(/\/schedule/)
    await expect(page.locator('header.topbar')).toContainText('Schedule')
    await expect(nav.locator('a.nav-item.active', { hasText: 'Schedule' })).toBeVisible()

    // Lesson Dashboard
    await nav.locator('a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)
    await expect(page.locator('header.topbar')).toContainText('Lesson Dashboard')
    await expect(nav.locator('a.nav-item.active', { hasText: 'Lesson Dashboard' })).toBeVisible()

    // Finances is Admin-only in the sidebar; navigate only if visible.
    const finances = nav.locator('a.nav-item', { hasText: 'Finances' })
    if (await finances.count()) {
      await finances.click()
      await page.waitForURL(/\/finances/)
      await expect(page.locator('header.topbar')).toContainText('Finances')
    } else {
      console.log('[info] Test user is not Admin — Finances nav item hidden (expected per BR s.12).')
    }

    // Urgent News
    await nav.locator('a.nav-item', { hasText: 'Urgent News' }).click()
    await page.waitForURL(/\/urgent/)
    await expect(page.locator('header.topbar')).toContainText('Urgent News')

    // Unknown route redirects to /schedule (catch-all), not a 404 page.
    await page.goto('/definitely-not-a-real-route')
    await page.waitForURL(/\/schedule/)
    await expect(page.locator('header.topbar')).toContainText('Schedule')

    expect(notFound, `404 responses hit: ${notFound.join(', ')}`).toHaveLength(0)
  })
})
