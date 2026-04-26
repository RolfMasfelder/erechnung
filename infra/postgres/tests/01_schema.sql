-- pgTAP Schema Tests: Tabellenstruktur und Constraints
-- Keine Testdaten erforderlich, läuft auf leerem Schema
-- Ausführung: via Django TestCase (test_pgtap_db.py)

BEGIN;

SELECT plan(57);

-- ============================================================
-- 1. TABELLEN VORHANDEN
-- ============================================================
SELECT has_table('public', 'invoice_app_invoice',         'Tabelle invoice_app_invoice existiert');
SELECT has_table('public', 'invoice_app_invoiceline',     'Tabelle invoice_app_invoiceline existiert');
SELECT has_table('public', 'invoice_app_businesspartner', 'Tabelle invoice_app_businesspartner existiert');
SELECT has_table('public', 'invoice_app_company',         'Tabelle invoice_app_company existiert');
SELECT has_table('public', 'invoice_app_product',         'Tabelle invoice_app_product existiert');
SELECT has_table('public', 'invoice_app_country',         'Tabelle invoice_app_country existiert');
SELECT has_table('public', 'auth_user',                   'Tabelle auth_user existiert');

-- ============================================================
-- 2. PRIMARY KEYS
-- ============================================================
SELECT has_pk('public', 'invoice_app_invoice',         'Invoice hat Primary Key');
SELECT has_pk('public', 'invoice_app_invoiceline',     'InvoiceLine hat Primary Key');
SELECT has_pk('public', 'invoice_app_businesspartner', 'BusinessPartner hat Primary Key');
SELECT has_pk('public', 'invoice_app_company',         'Company hat Primary Key');
SELECT has_pk('public', 'invoice_app_product',         'Product hat Primary Key');

-- ============================================================
-- 3. WICHTIGE SPALTEN VORHANDEN (invoice_app_invoice)
-- ============================================================
SELECT has_column('public', 'invoice_app_invoice', 'invoice_number', 'Invoice hat Spalte invoice_number');
SELECT has_column('public', 'invoice_app_invoice', 'status',         'Invoice hat Spalte status');
SELECT has_column('public', 'invoice_app_invoice', 'invoice_type',   'Invoice hat Spalte invoice_type');
SELECT has_column('public', 'invoice_app_invoice', 'total_amount',   'Invoice hat Spalte total_amount');
SELECT has_column('public', 'invoice_app_invoice', 'subtotal',       'Invoice hat Spalte subtotal');
SELECT has_column('public', 'invoice_app_invoice', 'tax_amount',     'Invoice hat Spalte tax_amount');
SELECT has_column('public', 'invoice_app_invoice', 'company_id',     'Invoice hat FK company_id');
SELECT has_column('public', 'invoice_app_invoice', 'business_partner_id', 'Invoice hat FK business_partner_id');

-- ============================================================
-- 4. WICHTIGE SPALTEN VORHANDEN (weitere Tabellen)
-- ============================================================
SELECT has_column('public', 'invoice_app_invoiceline', 'invoice_id',    'InvoiceLine hat FK invoice_id');
SELECT has_column('public', 'invoice_app_invoiceline', 'quantity',      'InvoiceLine hat Spalte quantity');
SELECT has_column('public', 'invoice_app_invoiceline', 'unit_price',    'InvoiceLine hat Spalte unit_price');
SELECT has_column('public', 'invoice_app_invoiceline', 'line_total',    'InvoiceLine hat Spalte line_total');
SELECT has_column('public', 'invoice_app_invoiceline', 'tax_rate',      'InvoiceLine hat Spalte tax_rate');
SELECT has_column('public', 'invoice_app_businesspartner', 'partner_number', 'BusinessPartner hat partner_number');
SELECT has_column('public', 'invoice_app_businesspartner', 'partner_type', 'BusinessPartner hat partner_type');
SELECT has_column('public', 'invoice_app_company', 'tax_id',            'Company hat tax_id');
SELECT has_column('public', 'invoice_app_product', 'product_code',      'Product hat product_code');
SELECT has_column('public', 'invoice_app_product', 'tax_category',      'Product hat tax_category');

-- ============================================================
-- 5. NOT NULL CONSTRAINTS
-- ============================================================
SELECT col_not_null('public', 'invoice_app_invoice', 'invoice_number', 'invoice_number darf nicht NULL sein');
SELECT col_not_null('public', 'invoice_app_invoice', 'status',         'status darf nicht NULL sein');
SELECT col_not_null('public', 'invoice_app_invoice', 'total_amount',   'total_amount darf nicht NULL sein');
SELECT col_not_null('public', 'invoice_app_businesspartner', 'partner_number', 'partner_number darf nicht NULL sein');
SELECT col_not_null('public', 'invoice_app_product', 'product_code',   'product_code darf nicht NULL sein');

-- ============================================================
-- 6. UNIQUE CONSTRAINTS
-- ============================================================
SELECT col_is_unique('public', 'invoice_app_invoice',         'invoice_number', 'invoice_number ist eindeutig');
SELECT col_is_unique('public', 'invoice_app_businesspartner', 'partner_number',   'partner_number ist eindeutig');
SELECT col_is_unique('public', 'invoice_app_product',         'product_code',   'product_code ist eindeutig');
SELECT col_is_unique('public', 'invoice_app_company',         'tax_id',         'tax_id ist eindeutig');

-- ============================================================
-- 7. FOREIGN KEYS
-- ============================================================
SELECT has_fk('public', 'invoice_app_invoice',     'invoice_app_invoice hat mindestens einen FK');
SELECT has_fk('public', 'invoice_app_invoiceline', 'invoice_app_invoiceline hat mindestens einen FK');

-- ============================================================
-- 8. DATENTYPEN (kritische Felder)
-- ============================================================
SELECT col_type_is('public', 'invoice_app_invoice', 'total_amount', 'numeric(15,2)', 'total_amount ist numeric(15,2)');
SELECT col_type_is('public', 'invoice_app_invoice', 'subtotal',     'numeric(15,2)', 'subtotal ist numeric(15,2)');
SELECT col_type_is('public', 'invoice_app_invoice', 'tax_amount',   'numeric(15,2)', 'tax_amount ist numeric(15,2)');
SELECT col_type_is('public', 'invoice_app_invoiceline', 'quantity',  'numeric(15,3)', 'quantity ist numeric(15,3)');
SELECT col_type_is('public', 'invoice_app_invoiceline', 'unit_price','numeric(15,6)', 'unit_price ist numeric(15,6)');

-- ============================================================
-- 9. EXTENSIONS VORHANDEN
-- ============================================================
SELECT has_extension('pgtap',              'Extension pgtap ist installiert');
SELECT has_extension('pg_stat_statements', 'Extension pg_stat_statements ist installiert');
SELECT has_extension('pg_trgm',            'Extension pg_trgm ist installiert');
SELECT has_extension('unaccent',           'Extension unaccent ist installiert');
SELECT has_extension('btree_gin',          'Extension btree_gin ist installiert');

-- ============================================================
-- 10. CHECK CONSTRAINTS: unit_of_measure (UnitOfMeasure-Sync)
-- Prüft ob die DB-Constraints existieren UND die richtigen Werte
-- enthalten (PCE=1, HUR=2, DAY=3, KGM=4, LTR=5, MON=6).
-- Schlägt fehl wenn UnitOfMeasure-Werte geändert wurden ohne
-- eine neue Migration zu erstellen.
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM pg_constraint WHERE conname = 'product_unit_of_measure_valid' AND contype = 'c'),
    'CHECK constraint product_unit_of_measure_valid existiert'
);
SELECT ok(
    EXISTS(SELECT 1 FROM pg_constraint WHERE conname = 'invoiceline_unit_of_measure_valid' AND contype = 'c'),
    'CHECK constraint invoiceline_unit_of_measure_valid existiert'
);

-- Constraint-Definitionen enthalten genau die Werte 1–6
SELECT ok(
    pg_get_constraintdef(oid) ~ '\m[1-6]\M',
    'product_unit_of_measure_valid enthält Werte 1–6 (PCE..MON)'
) FROM pg_constraint WHERE conname = 'product_unit_of_measure_valid';

SELECT ok(
    pg_get_constraintdef(oid) ~ '\m[1-6]\M',
    'invoiceline_unit_of_measure_valid enthält Werte 1–6 (PCE..MON)'
) FROM pg_constraint WHERE conname = 'invoiceline_unit_of_measure_valid';

SELECT finish();
ROLLBACK;
