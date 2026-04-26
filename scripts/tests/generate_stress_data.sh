#!/usr/bin/env bash
# =============================================================================
# Stress-Daten generieren für Update-Tests
# =============================================================================
# Generiert 10.000 Rechnungen + 500 Partner + 2.000 Audit via SQL.
# Wird von test_edge_infra.sh / test_edge_data.sh aufgerufen.
#
# Usage:
#   ./scripts/tests/generate_stress_data.sh <compose-file>
#
# Voraussetzung: DB muss migriert und minimal.json geladen sein.
# =============================================================================

set -euo pipefail

COMPOSE_FILE="${1:?Usage: $0 <compose-file>}"

psql_test() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -t -A -c "$1" 2>/dev/null
}

psql_exec() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "$1" &>/dev/null
}

echo "  Generating stress data..."

# 1. Generate 500 business partners
echo "  → 500 Business Partners..."
psql_exec "
INSERT INTO invoice_app_businesspartner
    (partner_number, company_name, first_name, last_name, legal_name,
     tax_id, vat_id, commercial_register,
     is_customer, is_supplier, partner_type,
     address_line1, address_line2, postal_code, city, state_province, country,
     phone, fax, email, website,
     is_active, payment_terms, preferred_currency,
     default_reference_prefix, contact_person, accounting_contact, accounting_email,
     created_at, updated_at)
SELECT
    'BP-STRESS-' || LPAD(g::text, 6, '0'),
    'Stress Partner ' || g, '', '', '',
    '', '', '',
    true, false, 'BUSINESS',
    'Straße ' || g, '', LPAD((g % 99999)::text, 5, '0'), 'Stadt ' || (g % 100), '', 'DE',
    '', '', 'stress' || g || '@test.local', '',
    true, 30, 'EUR',
    '', '', '', '',
    NOW(), NOW()
FROM generate_series(1, 500) AS g
ON CONFLICT DO NOTHING;
"

PARTNER_COUNT=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
echo "  → Partners total: $PARTNER_COUNT"

# 2. Get company and user for invoice FK
COMPANY_ID=$(psql_test "SELECT id FROM invoice_app_company LIMIT 1;")
USER_ID=$(psql_test "SELECT id FROM auth_user LIMIT 1;")
PARTNER_MIN=$(psql_test "SELECT MIN(id) FROM invoice_app_businesspartner WHERE is_customer=true;")
PARTNER_MAX=$(psql_test "SELECT MAX(id) FROM invoice_app_businesspartner WHERE is_customer=true;")

if [[ -z "$COMPANY_ID" || -z "$USER_ID" ]]; then
    echo "  ERROR: Company or User missing — load minimal.json first" >&2
    exit 1
fi

# 3. Generate 10,000 invoices
echo "  → 10,000 Invoices..."
psql_exec "
INSERT INTO invoice_app_invoice
    (invoice_number, invoice_type, company_id, business_partner_id,
     issue_date, due_date, currency,
     subtotal, tax_amount, total_amount,
     status, payment_terms, payment_method, payment_reference,
     buyer_reference, seller_reference,
     content_hash, hash_algorithm, deletion_blocked,
     is_archived, is_locked, lock_reason,
     created_by_id, notes, created_at, updated_at)
SELECT
    'RE-STRESS-' || LPAD(g::text, 6, '0'),
    CASE WHEN g % 20 = 0 THEN 'CREDIT_NOTE' ELSE 'INVOICE' END,
    $COMPANY_ID,
    $PARTNER_MIN + (g % ($PARTNER_MAX - $PARTNER_MIN + 1)),
    '2026-01-01'::date + (g % 365),
    '2026-02-01'::date + (g % 365),
    'EUR',
    (100 + (g % 9900))::numeric,
    ((100 + (g % 9900)) * 0.19)::numeric(12,2),
    ((100 + (g % 9900)) * 1.19)::numeric(12,2),
    CASE g % 10
        WHEN 0 THEN 'DRAFT'
        WHEN 1 THEN 'DRAFT'
        WHEN 2 THEN 'DRAFT'
        WHEN 3 THEN 'SENT'
        WHEN 4 THEN 'SENT'
        WHEN 5 THEN 'SENT'
        WHEN 6 THEN 'PAID'
        WHEN 7 THEN 'PAID'
        WHEN 8 THEN 'PAID'
        ELSE 'CANCELLED'
    END,
    30,
    '', '', '', '',
    '', 'SHA256', false,
    false, false, '',
    $USER_ID,
    'Stress-Test Rechnung #' || g,
    NOW(), NOW()
FROM generate_series(1, 10000) AS g
ON CONFLICT DO NOTHING;
"

INVOICE_COUNT=$(psql_test "SELECT COUNT(*) FROM invoice_app_invoice;")
echo "  → Invoices total: $INVOICE_COUNT"

# 4. Generate 2,000 audit entries
echo "  → 2,000 Audit Entries..."
psql_exec "
INSERT INTO invoice_app_auditlog
    (event_id, user_id, username, session_key, action, object_type, object_id,
     object_repr, description, details, ip_address, user_agent, severity,
     is_compliance_relevant, is_security_event,
     server_name, application_version,
     old_values, new_values,
     entry_hash, previous_entry_hash,
     timestamp)
SELECT
    gen_random_uuid(),
    $USER_ID,
    'testadmin',
    '',
    CASE g % 5
        WHEN 0 THEN 'CREATE'
        WHEN 1 THEN 'READ'
        WHEN 2 THEN 'UPDATE'
        WHEN 3 THEN 'EXPORT'
        ELSE 'GENERATE_PDF'
    END,
    CASE WHEN g % 2 = 0 THEN 'Invoice' ELSE 'BusinessPartner' END,
    (1 + (g % GREATEST($INVOICE_COUNT, 1)))::text,
    'Stress object #' || g,
    'Stress test audit entry #' || g,
    '{\"stress_test\": true}'::jsonb,
    '127.0.0.1',
    '',
    'INFO',
    g % 10 = 0,
    false,
    'stress-test',
    '1.0.0',
    '{}'::jsonb,
    '{}'::jsonb,
    md5(g::text),
    md5((g - 1)::text),
    NOW() - (g || ' minutes')::interval
FROM generate_series(1, 2000) AS g;
"

AUDIT_COUNT=$(psql_test "SELECT COUNT(*) FROM invoice_app_auditlog;")
echo "  → Audit entries total: $AUDIT_COUNT"

echo "  Stress data generation complete."
echo "  → Partners: $PARTNER_COUNT, Invoices: $INVOICE_COUNT, Audit: $AUDIT_COUNT"
