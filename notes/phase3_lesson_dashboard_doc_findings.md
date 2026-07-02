# Phase 3 / Phase 4 Lesson Dashboard document findings

## Source priority
1. **Lesson Dashboard PRD**
2. **Vinci Automation Phased Development Plan**
3. **Business Rules v1.2**

## Lesson Dashboard PRD — key requirements

### Vision and philosophy
- Goal: provide a page for the admin to view all **unassigned lessons** and perform **manual assignment** when necessary.
- Core principle: **lesson status synchronization** — any manual tutor assignment must update the lesson directly in the database and stay synchronized with the schedule/calendar.
- Core principle: **importance sorting** — lessons should be sorted from the closest date to the farthest date from the current date.

### User journey
- Jay opens the Lesson Dashboard to check **unassigned lessons** and manually assign tutors to lessons within a week.
- Rows start with **lesson ID** on the left, then **course name**, then **date & time**.
- Each row has an **assign tutor** button on the far right.
- Clicking the button opens a **slideout panel** showing tutors who have accepted the offer through WhatsApp.
- Tutors in that panel are sorted from **highest score to lowest score**.
- Jay selects the appropriate tutors for the lesson and repeats this for all lessons within a week.

### Functional requirements
- **Data updating:** changes done on the dashboard, including manual tutor assignment, must update the database directly.
- **Disappearing rows:** if the appropriate number of tutors has been selected, the corresponding lesson should no longer appear on the dashboard.
- **Data clash handling:**
  - If a lesson already has an assigned tutor and the admin tries to re-assign a different tutor, a **warning pop-up** must appear.
  - If the admin tries to assign the **same tutor twice**, an **error message** must appear.
- **Urgency sorting:**
  - Lessons with **no tutors accepted** appear first.
  - Then lessons with **accepted tutors but no selected tutors**.
  - Both groups are sorted from the closest date to the farthest date from the current day.

### Delivery boundary
- The dashboard primarily displays lessons that require the admin's attention and action, specifically lessons with **no assigned tutors**.

## Phased development plan — key findings relevant to this work

### Phase map
- The phased plan labels **Lesson Dashboard as Phase 4**, after Platform Foundation, Data Input & Chatbot Assistant, and Lesson Calendar.
- The user's current instruction is to continue with the Lesson Dashboard and prioritize document truth in the order above.

### Sequencing logic
- Foundation -> data entry -> visualization -> assignment workflow -> reporting -> exception handling.
- This confirms the Lesson Dashboard should sit on top of the existing shell, data-entry system, and lesson calendar.

### Important implications from the plan
- The operational dashboard depends on lessons, courses, teachers, and schools already being present in the database.
- The dashboard should be tightly integrated with the schedule/calendar because both operate on the same lesson records.
- The dashboard's emphasis is **admin actionability**, not general reporting.

## Immediate build implications to audit next
- Confirm current dashboard focuses on **unassigned / action-needed lessons**, not all lessons equally.
- Confirm current ordering matches the PRD's urgency logic:
  1. no accepted tutors
  2. accepted tutors but none selected
  3. nearest date first within each group
- Confirm row layout includes lesson ID, course name, date, and time.
- Confirm slideout assignment panel lists only accepted tutors and sorts them by score descending.
- Confirm assignment updates remove resolved lessons from the dashboard.
- Confirm clash handling exists for reassignment and duplicate-tutor assignment.
- Confirm synchronization with the calendar remains intact after any assignment.

## Remaining document work
- Read the **Business Rules v1.2** sections for lesson schema, tutor scoring, assignment logic, and any status or income rules that refine the PRD.
- Audit the existing backend and frontend against the above requirements before implementing changes.

## Additional findings from the phased development plan (pages 6-12)

The phased plan confirms that the existing **Lesson Calendar** is a prerequisite dependency for the Lesson Dashboard because both features operate on the same lesson records and share assignment-state behavior. The calendar phase explicitly requires that lesson-detail side panels reflect school, date and time, assigned tutors, number of tutors, lesson income, and lesson material links, and it states that calendar colors depend on whether a lesson is still unassigned and how close the lesson date is. This matters for the current phase because any dashboard-side assignment must immediately turn the lesson into the correct assigned state and therefore change its appearance on the calendar.

| Source | Confirmed requirement | Implementation implication |
| --- | --- | --- |
| Phased Development Plan, Lesson Dashboard phase (page 8) | Build lesson rows with **Lesson ID**, **Course name**, **Date & Time**, and an **Assign Tutor** button on the right | The current dashboard layout must be audited against this exact row structure |
| Phased Development Plan, Lesson Dashboard phase (page 8) | Sort lessons with **zero accepted tutors first**, then **accepted-but-unselected tutors**, with each group **closest date first** | Sorting logic belongs in the dashboard query and should not rely only on client-side display ordering |
| Phased Development Plan, Lesson Dashboard phase (page 8) | Clicking **Assign Tutor** opens a slideout listing every teacher who accepted via WhatsApp, sorted **highest score to lowest score** | The backend must return accepted tutors only, along with a score field that can be reliably sorted |
| Phased Development Plan, Lesson Dashboard phase (page 8) | Selecting tutors writes directly to the database, and the lesson disappears once enough tutors are selected | Assignment must trigger status recalculation and the dashboard dataset must exclude fully resolved lessons immediately |
| Phased Development Plan, Lesson Dashboard phase (page 8) | Reassigning a different tutor to an already-assigned lesson shows a **warning**; assigning the same tutor twice shows an **error** | Both clash detection and duplicate-assignment validation must exist in the assignment flow |
| Phased Development Plan, Lesson Dashboard phase (page 8) | A completed assignment must reflect instantly on the **Calendar** and remove the lesson from the **Urgent** page if flagged there | Shared invalidation or re-fetch behavior must continue to work across all views |

The phased plan's evaluation criteria make the success conditions explicit. A lesson with zero accepted tutors must always rank above one with accepted-but-unselected tutors, each urgency group must still sort by date, assigning the required number of tutors must remove the lesson from the dashboard automatically, and the validation behavior for reassignment and duplicate tutor selection must be visible to the admin.

The later plan pages also matter because they describe downstream dependencies. The **Urgent Situations Page** is designed to reuse the same tutor-pool picker as the Lesson Dashboard for manual reassignment and for soon-unassigned lessons. That means the current dashboard-side assignment UI should be built in a reusable way rather than as an isolated one-off implementation.

## Remaining required reading

The remaining primary document work is now complete for the phased plan. The next required document is **Vinci_AI_Automation_Business_Rules_v1.2.docx**, which still needs to be re-read for tutor scoring, assignment constraints, and any rule details that refine but do not override the PRD.
