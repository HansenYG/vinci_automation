# Manual Test Checklist — Admin Verification

**What this is:** a plain-language checklist to verify the three fixes that were
just released. No technical knowledge needed — just use the website like you
normally would and tick each box.

**What you need before starting:**

- Your admin login for https://vinci-automation.vercel.app
- A second browser tab you can switch to (any website)
- For Test 2 only: a test lesson and a tutor (or test phone) who can reply on WhatsApp

**How to use:** do each test, then tick **Pass** or **Fail**. If anything fails,
note what you saw in the "Notes" column and send it to your developer.

---

## Test 1 — Switching tabs should NOT refresh the page

| # | Step | What you should see | Result |
|---|------|--------------------|--------|
| 1.1 | Log in and open the **Lesson Dashboard**. | The dashboard loads normally. | ☐ Pass ☐ Fail |
| 1.2 | Type a word into the **search box** (don't clear it). | Your text stays in the box. | ☐ Pass ☐ Fail |
| 1.3 | Switch to a different browser tab for **at least 1 minute**, then come back. | The page looks **exactly** as you left it — your search text is still there. You do **not** see a "Checking your access…" screen, and the page does **not** reload or flicker. | ☐ Pass ☐ Fail |
| 1.4 | Open the **Schedule** page, click a lesson so the detail panel slides out, then switch tabs for a minute and come back. | The panel is still open, same lesson, nothing reloaded. | ☐ Pass ☐ Fail |
| 1.5 | Repeat 1.3 two or three more times over ~10 minutes. | Same result every time — the page never refreshes itself. | ☐ Pass ☐ Fail |

**Notes:** _______________________________________________

---

## Test 2 — When a tutor cancels on WhatsApp

> 📌 **Behaviour change:** a tutor cancelling no longer cancels the whole lesson.
> Only that tutor is removed; the lesson stays active and goes back to
> Unassigned/Offer Sent (red = within 7 days, yellow = further out) so a
> replacement can be found. "Cancelled" (grey) is now only for lessons the
> admin calls off entirely.

**Setup:** pick (or create) one real test lesson that is assigned to a tutor who
can reply to your WhatsApp messages. Ideally the lesson is within the next 7 days.

| # | Step | What you should see | Result |
|---|------|--------------------|--------|
| 2.1 | Have the tutor reply **"cancel"** to the lesson message on WhatsApp. | The tutor gets the usual automated reply (if any). | ☐ Pass ☐ Fail |
| 2.2 | Within a minute, check **your own admin WhatsApp**. | You receive a message saying the tutor cancelled, naming the **tutor, lesson, course, date, and time**. | ☐ Pass ☐ Fail |
| 2.3 | Open the **Schedule** page and click that lesson. | The tutor is removed, but the lesson stays **active** — it is **not** marked "Cancelled". Its status shows **Unassigned / Offer Sent**: a **red** badge if the lesson is within 7 days, **yellow** if it's further out. *(Multi-tutor lessons: if the remaining tutors still fill all required slots, the lesson simply stays **Assigned** (green).)* | ☐ Pass ☐ Fail |
| 2.4 | Ask another tutor (or check with one) whether they received a new WhatsApp offer for that lesson. | Other suitable tutors get a fresh offer automatically (the system looks for a replacement). The tutor who cancelled does **not** get one. | ☐ Pass ☐ Fail |
| 2.5 | Have another tutor reply **"Accept"** to that offer. | The lesson status changes to **Has Acceptance** (yellow) — it no longer shows as unassigned. | ☐ Pass ☐ Fail |
| 2.6 | Open the **Lesson Dashboard**. | The lesson from 2.5 appears in the pending-approvals banner (see Test 3). | ☐ Pass ☐ Fail |

> ⚠️ **If step 2.2 fails (no admin WhatsApp):** the most likely cause is that the
> admin phone number is not configured on the server. Tell your developer:
> *"Check the `ADMIN_WHATSAPP` setting on Render"* — the system now records every
> skipped notification, so they can confirm it quickly.

**Notes:** _______________________________________________

---

## Test 3 — Pending tutor approvals are obvious on the dashboard

**Setup:** you need at least one lesson where a tutor has replied "Accept" but
you have not yet assigned them (step 2.5 creates one, or use an existing one).

| # | Step | What you should see | Result |
|---|------|--------------------|--------|
| 3.1 | Open the **Lesson Dashboard**. | A **bright amber/yellow banner** at the very top saying how many lessons have tutor applications awaiting approval. | ☐ Pass ☐ Fail |
| 3.2 | Click **"Review now"** in the banner. | The table filters to show **only** those lessons. | ☐ Pass ☐ Fail |
| 3.3 | Look at the filtered rows. | Each row is **tinted amber** with a yellow bar on the left, and the status shows an **"⏳ Approval needed"** chip. | ☐ Pass ☐ Fail |
| 3.4 | Click **"Clear filters"**, then click the **"Pending Approvals"** stat card (the yellow-numbered card). | The table filters to the same pending lessons — the card works like a shortcut. | ☐ Pass ☐ Fail |
| 3.5 | Click a pending lesson and **assign the tutor** as usual. | After assigning, reopen the dashboard: the banner count has gone **down by one**, and that lesson no longer shows "Approval needed". | ☐ Pass ☐ Fail |
| 3.6 | When **no** lessons are awaiting approval, reload the dashboard. | The amber banner is **completely hidden** — it only appears when there is something to approve. | ☐ Pass ☐ Fail |

**Notes:** _______________________________________________

---

## Sign-off

| | |
|---|---|
| Tested by: | _______________________ |
| Date: | _______________________ |
| Overall result: | ☐ All passed ☐ Issues found (see notes) |
