-- pgTAP Business Logic & Daten-Integritätstests
-- Setzt voraus: create_test_data wurde ausgeführt
-- Ausführung: via Django TestCase (test_pgtap_db.py)

BEGIN;

SELECT plan(22);

-- ============================================================
-- 1. TESTDATEN VORHANDEN (Voraussetzung)
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) FROM invoice_app_invoice) > 0,
    'Rechnungen wurden durch create_test_data angelegt'
);
SELECT ok(
    (SELECT COUNT(*) FROM invoice_app_businesspartner) > 0,
    'Business Partner wurden angelegt'
);
SELECT ok(
    (SELECT COUNT(*) FROM invoice_app_product) > 0,
    'Produkte wurden angelegt'
);
SELECT ok(
    (SELECT COUNT(*) FROM invoice_app_company) > 0,
    'Mindestens eine Company existiert'
);

-- ============================================================
-- 2. INVOICE STATUS: nur erlaubte Werte
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice
     WHERE status NOT IN ('DRAFT', 'SENT', 'PAID', 'CANCELLED', 'OVERDUE')),
    0::bigint,
    'Alle Invoice-Status sind gültige Werte'
);

-- ============================================================
-- 3. INVOICE TYPE: nur erlaubte Werte
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice
     WHERE invoice_type NOT IN ('INVOICE', 'CREDIT_NOTE', 'DEBIT_NOTE', 'CORRECTED', 'PARTIAL', 'FINAL')),
    0::bigint,
    'Alle Invoice-Types sind gültige Werte'
);

-- ============================================================
-- 4. GESCHÄFTSPARTNER: nur erlaubte Typen
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_businesspartner
     WHERE partner_type NOT IN ('INDIVIDUAL', 'BUSINESS', 'GOVERNMENT', 'NON_PROFIT')),
    0::bigint,
    'Alle Partner-Typen sind gültige Werte'
);

-- ============================================================
-- 5. PRODUKTE: nur erlaubte Typen und Steuerkategorien
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_product
     WHERE product_type NOT IN ('PHYSICAL', 'SERVICE', 'DIGITAL', 'SUBSCRIPTION')),
    0::bigint,
    'Alle Product-Types sind gültige Werte'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_product
     WHERE tax_category NOT IN ('STANDARD', 'REDUCED', 'ZERO', 'EXEMPT', 'REVERSE_CHARGE')),
    0::bigint,
    'Alle Tax-Kategorien sind gültige Werte'
);

-- ============================================================
-- 6. BETRÄGE: keine negativen Werte
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice WHERE total_amount < 0),
    0::bigint,
    'Keine Rechnung hat negativen total_amount'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice WHERE subtotal < 0),
    0::bigint,
    'Keine Rechnung hat negativen subtotal'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice WHERE tax_amount < 0),
    0::bigint,
    'Keine Rechnung hat negativen tax_amount'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoiceline WHERE quantity <= 0),
    0::bigint,
    'Keine InvoiceLine hat quantity <= 0'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoiceline WHERE unit_price < 0),
    0::bigint,
    'Keine InvoiceLine hat negativen unit_price'
);

-- ============================================================
-- 7. REFERENTIELLE INTEGRITÄT (zusätzlich zu DB-FKs)
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice i
     LEFT JOIN invoice_app_company c ON i.company_id = c.id
     WHERE c.id IS NULL),
    0::bigint,
    'Alle Rechnungen referenzieren eine existierende Company'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice i
     LEFT JOIN invoice_app_businesspartner bp ON i.business_partner_id = bp.id
     WHERE i.business_partner_id IS NOT NULL AND bp.id IS NULL),
    0::bigint,
    'Alle Rechnungen referenzieren existierende Business Partner'
);
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoiceline il
     LEFT JOIN invoice_app_invoice i ON il.invoice_id = i.id
     WHERE i.id IS NULL),
    0::bigint,
    'Alle InvoiceLines haben eine gültige Invoice-Referenz'
);

-- ============================================================
-- 8. INVOICE NUMBER FORMAT (nur Buchstaben, Zahlen, Bindestriche)
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM invoice_app_invoice
     WHERE invoice_number !~ '^[A-Za-z0-9-]+$'),
    0::bigint,
    'Alle invoice_numbers entsprechen dem erlaubten Format'
);

-- ============================================================
-- 9. DUPLIKATE PRÜFEN
-- ============================================================
SELECT is(
    (SELECT COUNT(*) FROM (
        SELECT invoice_number, COUNT(*) FROM invoice_app_invoice
        GROUP BY invoice_number HAVING COUNT(*) > 1
    ) dupes),
    0::bigint,
    'Keine duplizierten invoice_numbers'
);
SELECT is(
    (SELECT COUNT(*) FROM (
        SELECT product_code, COUNT(*) FROM invoice_app_product
        GROUP BY product_code HAVING COUNT(*) > 1
    ) dupes),
    0::bigint,
    'Keine duplizierten product_codes'
);

-- ============================================================
-- 10. TRIGRAM-INDEX nutzbar (pg_trgm vorhanden)
-- ============================================================
SELECT ok(
    (SELECT similarity('Mustermann GmbH', 'Mustermann GmbH & Co') > 0.3),
    'pg_trgm similarity() funktioniert'
);

-- ============================================================
-- 11. UNACCENT funktioniert
-- ============================================================
SELECT is(
    unaccent('Müller'),
    'Muller',
    'unaccent() normalisiert deutsche Umlaute'
);

SELECT finish();
ROLLBACK;
