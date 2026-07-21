// @ts-check
import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Automated version of Downloads/manual_test_checklist.md.
 *
 *   Test 1 — tab switching must not refresh the page (local + prod)
 *   Test 2 — tutor cancellation flow (LOCAL ONLY: simulates the WATI webhook
 *            against the local backend; on prod this would send real WhatsApp
 *            messages to real tutors, so it is skipped there)
 *   Test 3 — pending-approvals banner (local: full flow incl. UI assign;
 *            prod: read-only checks)
 *
 * NOTE vs the paper checklist: step 2.3 there expects status "Cancelled" —
 * that was the bug we removed. The new correct expectation is: tutor removed,
 * lesson stays active as Unassigned/Offer Sent (red <=7 days, yellow beyond),
 * then Has Acceptance when a new tutor accepts.
 *
 * Run local:  E2E_BASE_URL=http://localhost:5173 npx playwright test tests/checklist.spec.js
 * Run prod:   npx playwright test tests/checklist.spec.js
 */

const EMAIL = process.env.E2E_EMAIL || 'hansenyg@vinciai.academy'
const PASSWORD = process.env.E2E_PASSWORD || 'VinciBeta2026!'

const REPO = path.resolve(process.cwd(), '..')
const BASE = process.env.E2E_BASE_URL || 'https://vinci-automation.vercel.app'
const LOCAL = /localhost|127\.0\.0\.1/.test(BASE)
const API = 'http://localhost:8000/api'

// ── Local-backend helpers (read backend/.env; secrets never printed) ────────

function backendEnv() {
  const env = {}
  for (const line of fs.readFileSync(path.join(REPO, 'backend', '.env'), 'utf8').split(/\r?\n/)) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/)
    if (m) env[m[1]] = m[2].trim().replace(/^["']|["']$/g, '')
  }
  return env
}

async function sb(env, method, table, { query = '', body, prefer } = {}) {
  const res = await fetch(`${env.SUPABASE_URL}/rest/v1/${table}${query}`, {
    method,
    headers: {
      apikey: env.SUPABASE_KEY,
      Authorization: `Bearer ${env.SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      ...(prefer ? { Prefer: prefer } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${method} ${table}${query} -> ${res.status}: ${await res.text()}`)
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

async function webhook(env, phone, text) {
  const res = await fetch(`${API}/webhooks/wati`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${env.WATI_WEBHOOK_SECRET}` },
    body: JSON.stringify({ eventType: 'message', text, waId: phone, owner: false }),
  })
  return res.json()
}

// ── UI helpers ──────────────────────────────────────────────────────────────

async function login(page) {
  await page.goto('/login')
  await expect(page.locator('.auth-form')).toBeVisible()
  await page.locator('.auth-form input[type="email"]').fill(EMAIL)
  await page.locator('.auth-form input[type="password"]').fill(PASSWORD)
  await page.locator('button.auth-submit').click()
  await page.waitForURL(/\/schedule/, { timeout: 90_000 })
  await expect(page.locator('.auth-loader')).toHaveCount(0, { timeout: 90_000 })
  await expect(page.locator('aside.sidebar')).toBeVisible()
}

/** Switch to another tab for `ms`, firing the same blur/visibility events a
 *  real tab switch produces. Returns after the original page is front again. */
async function switchAwayFor(page, ms) {
  await page.evaluate(() => { window.__e2eMarker = 'alive' })
  const other = await page.context().newPage()
  await other.goto('https://example.com')
  await page.evaluate(() => {
    window.dispatchEvent(new Event('blur'))
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await page.waitForTimeout(ms)
  await page.bringToFront()
  await page.evaluate(() => { window.dispatchEvent(new Event('focus')) })
  await other.close()
  await page.waitForTimeout(1_500)
}

async function expectNoReload(page) {
  expect(await page.evaluate(() => window.__e2eMarker || null)).toBe('alive')
  await expect(page.locator('.auth-loader')).toHaveCount(0)
  await expect(page).not.toHaveURL(/\/login/)
}

// ── Test data (local only) ──────────────────────────────────────────────────

const T1 = { id: 'TEST-E2E-T1', phone: '85299990011' }
const T2 = { id: 'TEST-E2E-T2', phone: '85299990012' }
const LESSON_CODE = 'TEST-E2E-CHK'

// ── Test 1 — tab switching must not refresh the page ───────────────────────

test.describe('Test 1 — tab switching keeps page state', () => {
  test.setTimeout(300_000)

  test('1.1-1.3 dashboard search text survives >=1 min on another tab', async ({ page }) => {
    await login(page)
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)

    const search = page.locator('.ld-toolbar__search input')
    await search.fill('e2eprobe')
    await expect(search).toHaveValue('e2eprobe')

    await switchAwayFor(page, 65_000)

    await expectNoReload(page)
    await expect(search).toHaveValue('e2eprobe')
  })

  test('1.4 open lesson drawer survives tab switch', async ({ page }) => {
    await login(page)
    const chip = page.locator('button.chip').first()
    await expect(chip).toBeVisible({ timeout: 60_000 })
    await chip.click()
    await expect(page.locator('aside.drawer')).toBeVisible()

    await switchAwayFor(page, 65_000)

    await expectNoReload(page)
    await expect(page.locator('aside.drawer')).toBeVisible()
  })

  test('1.5 repeated tab switches never self-refresh', async ({ page }) => {
    await login(page)
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)

    for (let i = 0; i < 2; i++) {
      await switchAwayFor(page, 60_000)
      await expectNoReload(page)
      await expect(page.locator('aside.sidebar')).toBeVisible()
    }
  })
})

// ── Test 2 — tutor cancellation flow (local only) ──────────────────────────

test.describe('Test 2 — tutor cancellation (local webhook simulation)', () => {
  test.skip(!LOCAL, 'Prod run would send real WhatsApp blasts to real tutors — local only.')
  test.describe.configure({ mode: 'serial' })
  test.setTimeout(180_000)

  let env, lessonId

  test.beforeAll(async () => {
    env = backendEnv()
    await sb(env, 'POST', 'teachers', { body: { teacher_id: T1.id, teacher_name: 'E2E Tutor One', status: 'Active', whatsapp_number: T1.phone } })
    await sb(env, 'POST', 'teachers', { body: { teacher_id: T2.id, teacher_name: 'E2E Tutor Two', status: 'Active', whatsapp_number: T2.phone } })
    const date = new Date(Date.now() + 2 * 86400_000).toISOString().slice(0, 10)
    const rows = await sb(env, 'POST', 'lessons', {
      body: { lesson_id: LESSON_CODE, date, start_time: '10:00', end_time: '11:00', status: 'Assigned', max_tutors: 1, tutor_assignment: 'Tutor assigned', teacher_id: T1.id },
      prefer: 'return=representation',
    })
    lessonId = rows[0].id
    await sb(env, 'POST', 'lesson_tutor_offers', { body: { lesson_id: lessonId, teacher_id: T1.id, offer_status: 'assigned' } })
  })

  test.afterAll(async () => {
    if (!env) return
    const ids = [T1.id, T2.id].map((t) => `"${t}"`).join(',')
    const lessons = await sb(env, 'GET', 'lessons', { query: `?select=id&lesson_id=eq.${LESSON_CODE}` })
    for (const l of lessons || []) {
      await sb(env, 'DELETE', 'lesson_tutor_offers', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lesson_events', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lessons', { query: `?id=eq.${l.id}` })
    }
    await sb(env, 'DELETE', 'teachers', { query: `?teacher_id=in.(${ids})` })
  })

  test('2.1-2.4 cancel removes only the tutor, reopens the slot, re-blasts', async () => {
    // 2.1 tutor replies "cancel" (simulated WATI webhook)
    const res = await webhook(env, T1.phone, 'Sorry, I need to cancel this lesson')
    expect(res.intent).toBe('cancel')
    expect(res.status).toBe('OfferSent')
    expect(res.filled_slots).toBe(0)

    // 2.2 admin notification is recorded (WATI/ADMIN_WHATSAPP unset locally,
    // so the system must log admin_notify_skipped rather than stay silent)
    const events = await sb(env, 'GET', 'lesson_events', { query: `?lesson_id=eq.${lessonId}&select=event_type` })
    const types = (events || []).map((e) => e.event_type)
    expect(types.some((t) => t === 'admin_notified' || t === 'admin_notify_skipped')).toBeTruthy()

    // 2.3 NEW expected behaviour: lesson NOT Cancelled — tutor removed, slot
    // reopened, red because the lesson is within 7 days
    const raw = (await sb(env, 'GET', 'lessons', { query: `?id=eq.${lessonId}&select=status,teacher_id` }))[0]
    expect(raw.status).not.toBe('Cancelled')
    expect(raw.status).toBe('OfferSent')
    expect(raw.teacher_id).toBeNull()
    const view = (await sb(env, 'GET', 'lesson_schedule', { query: `?id=eq.${lessonId}&select=status,color,assigned_teacher_id` }))[0]
    expect(view.status).toBe('unassigned')
    expect(view.color).toBe('red')

    // 2.4 re-blast created fresh pending offers for other tutors, excluding T1
    const offers = await sb(env, 'GET', 'lesson_tutor_offers', { query: `?lesson_id=eq.${lessonId}&select=teacher_id,offer_status` })
    const pending = (offers || []).filter((o) => o.offer_status === 'pending')
    expect(pending.length).toBeGreaterThan(0)
    expect(pending.some((o) => o.teacher_id === T2.id)).toBeTruthy()
    expect(pending.some((o) => o.teacher_id === T1.id)).toBeFalsy()
  })

  test('2.5-2.6 another tutor accepts -> Has Acceptance + dashboard shows it', async ({ page }) => {
    const res = await webhook(env, T2.phone, 'Accept')
    expect(res.intent).toBe('accept')

    const raw = (await sb(env, 'GET', 'lessons', { query: `?id=eq.${lessonId}&select=status` }))[0]
    expect(raw.status).toBe('HasAcceptance')

    await login(page)
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)
    await expect(page.locator('.ld-pending-banner')).toBeVisible({ timeout: 60_000 })
  })
})

// ── Test 3 — pending-approvals banner ──────────────────────────────────────

test.describe('Test 3 — pending approvals on the dashboard', () => {
  test.describe.configure({ mode: 'serial' })
  test.setTimeout(180_000)

  const PEND_CODE = 'TEST-E2E-PEND'
  let env

  // Local runs seed their own HasAcceptance lesson so the banner/filter/assign
  // flow has something to work on (prod runs stay read-only).
  test.beforeAll(async () => {
    if (!LOCAL) return
    env = backendEnv()
    // Idempotent seed: clear any leftovers from previous runs first.
    const old = await sb(env, 'GET', 'lessons', { query: `?select=id&lesson_id=eq.${PEND_CODE}` })
    for (const l of old || []) {
      await sb(env, 'DELETE', 'lesson_tutor_offers', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lesson_events', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lessons', { query: `?id=eq.${l.id}` })
    }
    await sb(env, 'POST', 'teachers', { body: { teacher_id: T2.id, teacher_name: 'E2E Tutor Two', status: 'Active', whatsapp_number: T2.phone } }).catch(() => {})
    const date = new Date(Date.now() + 2 * 86400_000).toISOString().slice(0, 10)
    const rows = await sb(env, 'POST', 'lessons', {
      body: { lesson_id: PEND_CODE, date, start_time: '10:00', end_time: '11:00', status: 'HasAcceptance', max_tutors: 1, tutor_assignment: 'Tutor unassigned & class is within a week of today' },
      prefer: 'return=representation',
    })
    await sb(env, 'POST', 'lesson_tutor_offers', { body: { lesson_id: rows[0].id, teacher_id: T2.id, offer_status: 'accepted' } })
  })

  test.afterAll(async () => {
    if (!env) return
    const lessons = await sb(env, 'GET', 'lessons', { query: `?select=id&lesson_id=eq.${PEND_CODE}` })
    for (const l of lessons || []) {
      await sb(env, 'DELETE', 'lesson_tutor_offers', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lesson_events', { query: `?lesson_id=eq.${l.id}` })
      await sb(env, 'DELETE', 'lessons', { query: `?id=eq.${l.id}` })
    }
    await sb(env, 'DELETE', 'teachers', { query: `?teacher_id=eq.${T2.id}` })
  })

  test('3.1-3.4 banner, review filter, amber rows, stat-card shortcut', async ({ page }) => {
    await login(page)
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)

    const pendingCard = page.locator('.ld-stat.ld-stat--action', { hasText: 'Pending Approvals' })
    await expect(pendingCard).toBeVisible({ timeout: 60_000 })
    // Wait until the dashboard data has actually loaded (spinner gone)
    await expect(page.locator('.ld-table-wrap .spinner')).toHaveCount(0, { timeout: 60_000 })
    const count = Number(await pendingCard.locator('.ld-stat__count').innerText())
    console.log(`[info] pending approvals: ${count}`)

    const banner = page.locator('.ld-pending-banner')
    if (count === 0) {
      // 3.6 — banner completely hidden when nothing awaits approval
      await expect(banner).toHaveCount(0)
      console.log('[info] 0 pending — banner correctly hidden (3.6 PASS)')
      return
    }

    // 3.1 banner visible with count
    await expect(banner).toBeVisible()
    await expect(banner).toContainText('awaiting approval')

    // 3.2 Review now filters the table
    await banner.locator('.ld-pending-banner__btn').click()
    const pendingRows = page.locator('tr.ld-row--pending')
    await expect(pendingRows.first()).toBeVisible()
    expect(await pendingRows.count()).toBeGreaterThan(0)

    // 3.3 amber rows with the approval chip
    await expect(page.locator('.ld-approval-chip').first()).toBeVisible()
    await expect(page.locator('.ld-approval-chip').first()).toContainText('Approval needed')

    // 3.4 Clear filters, then the stat card filters to the same set
    await page.locator('button', { hasText: 'Clear filters' }).click()
    await pendingCard.click()
    await expect(page.locator('tr.ld-row--pending').first()).toBeVisible()
  })

  test('3.5-3.6 assign a pending tutor -> count drops; banner hides at zero', async ({ page }) => {
    test.skip(!LOCAL, 'Would mutate prod data — local only.')

    await login(page)
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)

    const pendingCard = page.locator('.ld-stat.ld-stat--action', { hasText: 'Pending Approvals' })
    // The seed guarantees >= 1 pending; wait for the banner so the count has loaded.
    await expect(page.locator('.ld-pending-banner')).toBeVisible({ timeout: 60_000 })
    const before = Number(await pendingCard.locator('.ld-stat__count').innerText())
    expect(before).toBeGreaterThan(0)

    // Open our seeded pending lesson and assign tutor two
    await page.locator('.ld-pending-banner__btn').click()
    await page.locator('tr', { hasText: PEND_CODE }).click()
    await expect(page.locator('aside.drawer')).toBeVisible()
    const respPromise = page.waitForResponse((r) => r.url().includes('/assign') && r.request().method() === 'POST', { timeout: 60_000 })
    await page.locator('aside.drawer .pool-row', { hasText: 'E2E Tutor Two' })
      .locator('button', { hasText: 'Assign' }).click()
    const assignResp = await respPromise
    expect(assignResp.status()).toBe(200)
    // Success shows up as either the drawer's "Assigned" state/flash message
    // or the drawer closing (dashboard onChanged closes it).
    await expect(async () => {
      const drawer = page.locator('aside.drawer')
      if ((await drawer.count()) === 0) return // closed after successful assign
      const text = await drawer.innerText()
      expect(text).toMatch(/Tutor assigned|ASSIGNED/)
    }).toPass({ timeout: 30_000 })

    // Backend agrees: fully staffed again -> Assigned/green
    const rows = await sb(env, 'GET', 'lesson_schedule', { query: `?lesson_code=eq.${PEND_CODE}&select=id,status,color,assigned_count` })
    const view = rows.find((r) => r.status === 'assigned') || rows[0]
    expect(view.status).toBe('assigned')
    expect(view.color).toBe('green')

    // Reopen the dashboard: banner count dropped by one (or hidden at zero)
    await page.reload()
    await expect(page.locator('.auth-loader')).toHaveCount(0, { timeout: 90_000 })
    await page.locator('aside.sidebar a.nav-item', { hasText: 'Lesson Dashboard' }).click()
    await page.waitForURL(/\/lessons/)
    await expect(page.locator('.ld-table-wrap .spinner')).toHaveCount(0, { timeout: 60_000 })
    const after = Number(await page.locator('.ld-stat.ld-stat--action .ld-stat__count').innerText())
    expect(after).toBe(before - 1)
    if (after === 0) {
      await expect(page.locator('.ld-pending-banner')).toHaveCount(0)
    }
  })
})
