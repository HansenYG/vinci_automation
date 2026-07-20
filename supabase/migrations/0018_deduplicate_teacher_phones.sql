-- 0018: Deduplicate teacher WhatsApp numbers.
-- One phone number = one tutor.  NULL out extras, then add a partial unique
-- index so the backend's phone‑matching helpers return at most one row.

-- For each group sharing a whatsapp_number, keep the lowest teacher_id
-- (earliest record) and null out the rest.
UPDATE teachers AS t
SET whatsapp_number = NULL
WHERE t.teacher_id NOT IN (
    SELECT MIN(t2.teacher_id)
    FROM teachers t2
    WHERE t2.whatsapp_number IS NOT NULL
    GROUP BY t2.whatsapp_number
);

-- Index: unique on non-null phone numbers only (Postgres partial index).
CREATE UNIQUE INDEX IF NOT EXISTS uq_teachers_whatsapp
    ON teachers (whatsapp_number)
    WHERE whatsapp_number IS NOT NULL;
