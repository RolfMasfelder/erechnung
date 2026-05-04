/**
 * Central Field Mapping Registry
 *
 * Every field that crosses the UI ↔ API boundary MUST be declared here.
 * "Accidental" name matches are not acceptable — even 1:1 fields are listed
 * so that a rename on either side is caught at a single location.
 *
 * Structure per entity:
 *   UI_TO_API  — { uiFieldName: 'apiFieldName' }
 *                 For 1:1 fields the value equals the key.
 *   UI_ONLY    — Set of field names that exist only in the UI and must
 *                 be stripped before sending to the API.
 *
 * The helper `createFieldMapper(mapping)` returns { toApi, fromApi } functions
 * that convert objects in both directions.
 */

// ---------------------------------------------------------------------------
// Generic helper
// ---------------------------------------------------------------------------

/**
 * Build a pair of converter functions from a mapping definition.
 *
 * @param {Object}      mapping
 * @param {Object}      mapping.UI_TO_API   – { uiField: 'apiField', … }
 * @param {Set<string>} [mapping.UI_ONLY]   – fields to drop before sending
 * @returns {{ toApi: (obj: Object) => Object, fromApi: (obj: Object) => Object }}
 */
export function createFieldMapper({ UI_TO_API, UI_ONLY = new Set() }) {
  // Pre-compute the reverse map once
  const API_TO_UI = Object.fromEntries(
    Object.entries(UI_TO_API).map(([ui, api]) => [api, ui]),
  )

  /** UI object → API payload (rename + strip UI-only fields) */
  function toApi(uiData) {
    const result = {}
    for (const [key, value] of Object.entries(uiData)) {
      if (UI_ONLY.has(key)) continue
      if (!(key in UI_TO_API)) continue        // unknown field — don't forward
      result[UI_TO_API[key]] = value
    }
    return result
  }

  /** API response → UI object (rename back) */
  function fromApi(apiData) {
    const result = {}
    for (const [key, value] of Object.entries(apiData)) {
      const uiKey = API_TO_UI[key] ?? key       // keep unmapped read-only fields (id, created_at, …)
      result[uiKey] = value
    }
    return result
  }

  return { toApi, fromApi, UI_TO_API, API_TO_UI }
}

// ---------------------------------------------------------------------------
// Entity definitions
// ---------------------------------------------------------------------------

// -- Invoice (header) -------------------------------------------------------
export const invoiceFields = createFieldMapper({
  UI_TO_API: {
    // writable fields the UI sends — 1:1 names
    company:          'company',
    business_partner: 'business_partner',
    invoice_number:   'invoice_number',
    invoice_type:     'invoice_type',
    issue_date:       'issue_date',
    due_date:         'due_date',
    delivery_date:    'delivery_date',
    currency:         'currency',
    payment_terms:    'payment_terms',
    payment_method:   'payment_method',
    payment_reference:'payment_reference',
    buyer_reference:  'buyer_reference',
    seller_reference: 'seller_reference',
    status:           'status',
    notes:            'notes',
    subtotal:         'subtotal',
    tax_amount:       'tax_amount',
    total_amount:     'total_amount',
    created_by:       'created_by',
    // Credit note / cancellation cross-references (read-only)
    cancelled_by:          'cancelled_by',
    cancelled_by_number:   'cancelled_by_number',
    cancelled_by_id:       'cancelled_by_id',
    cancels_invoice_number:'cancels_invoice_number',
    cancels_invoice_id:    'cancels_invoice_id',
    // Concurrent Edit Lock (read-only, set by server)
    editing_by_display:    'editing_by_display',
    editing_since:         'editing_since',
    // E-Mail-Versand-Tracking (read-only, set by server on send_email)
    last_emailed_at:       'last_emailed_at',
    last_email_recipient:  'last_email_recipient',
    // XRechnung B2G-Versand (read-only, set by server on send_xrechnung)
    xrechnung_sent_at:     'xrechnung_sent_at',
    xrechnung_sent_to:     'xrechnung_sent_to',
  },
})

// -- Invoice Line -----------------------------------------------------------
export const invoiceLineFields = createFieldMapper({
  UI_TO_API: {
    invoice:             'invoice',
    product:             'product',
    description:         'description',
    product_code:        'product_code',
    quantity:            'quantity',
    unit_price_net:      'unit_price',          // UI "unit_price_net" → API "unit_price"
    unit_of_measure:     'unit_of_measure',
    vat_rate:            'tax_rate',             // UI "vat_rate" → API "tax_rate"
    discount_percentage: 'discount_percentage',
    discount_amount:     'discount_amount',
    discount_reason:     'discount_reason',
  },
})

// -- Invoice Allowance / Charge (BG-20/BG-21) ------------------------------
export const allowanceChargeFields = createFieldMapper({
  UI_TO_API: {
    invoice:             'invoice',
    invoice_line:        'invoice_line',
    is_charge:           'is_charge',
    actual_amount:       'actual_amount',
    calculation_percent: 'calculation_percent',
    basis_amount:        'basis_amount',
    reason_code:         'reason_code',
    reason:              'reason',
    tax_rate:            'tax_rate',
    sort_order:          'sort_order',
  },
})

// -- Business Partner -------------------------------------------------------
export const businessPartnerFields = createFieldMapper({
  UI_TO_API: {
    name:                      'company_name',       // renamed
    street:                    'address_line1',       // renamed
    tax_number:                'tax_id',              // renamed
    // 1:1 fields — still explicit
    is_customer:               'is_customer',
    is_supplier:               'is_supplier',
    partner_type:              'partner_type',
    first_name:                'first_name',
    last_name:                 'last_name',
    legal_name:                'legal_name',
    vat_id:                    'vat_id',
    commercial_register:       'commercial_register',
    leitweg_id:                'leitweg_id',
    address_line2:             'address_line2',
    postal_code:               'postal_code',
    city:                      'city',
    state_province:            'state_province',
    country:                   'country',
    phone:                     'phone',
    fax:                       'fax',
    email:                     'email',
    website:                   'website',
    payment_terms:             'payment_terms',
    credit_limit:              'credit_limit',
    preferred_currency:        'preferred_currency',
    default_reference_prefix:  'default_reference_prefix',
    contact_person:            'contact_person',
    accounting_contact:        'accounting_contact',
    accounting_email:          'accounting_email',
    is_active:                 'is_active',
  },
  UI_ONLY: new Set(['notes']),
})

// -- Company ----------------------------------------------------------------
export const companyFields = createFieldMapper({
  UI_TO_API: {
    name:                  'name',
    legal_name:            'legal_name',
    tax_id:                'tax_id',
    vat_id:                'vat_id',
    commercial_register:   'commercial_register',
    address_line1:         'address_line1',
    address_line2:         'address_line2',
    postal_code:           'postal_code',
    city:                  'city',
    state_province:        'state_province',
    country:               'country',
    phone:                 'phone',
    fax:                   'fax',
    email:                 'email',
    website:               'website',
    logo:                  'logo',
    bank_name:             'bank_name',
    bank_account:          'bank_account',
    iban:                  'iban',
    bic:                   'bic',
    default_currency:      'default_currency',
    default_payment_terms: 'default_payment_terms',
    is_active:             'is_active',
  },
})

// -- Product ----------------------------------------------------------------
export const productFields = createFieldMapper({
  UI_TO_API: {
    product_code:          'product_code',
    name:                  'name',
    description:           'description',
    product_type:          'product_type',
    category:              'category',
    subcategory:           'subcategory',
    brand:                 'brand',
    manufacturer:          'manufacturer',
    base_price:            'base_price',
    currency:              'currency',
    cost_price:            'cost_price',
    list_price:            'list_price',
    unit_of_measure:       'unit_of_measure',
    weight:                'weight',
    dimensions:            'dimensions',
    tax_category:          'tax_category',
    default_tax_rate:      'default_tax_rate',
    tax_code:              'tax_code',
    track_inventory:       'track_inventory',
    stock_quantity:        'stock_quantity',
    minimum_stock:         'minimum_stock',
    barcode:               'barcode',
    sku:                   'sku',
    tags:                  'tags',
    is_active:             'is_active',
    is_sellable:           'is_sellable',
    discontinuation_date:  'discontinuation_date',
  },
})

// -- Attachment -------------------------------------------------------------
export const attachmentFields = createFieldMapper({
  UI_TO_API: {
    invoice:         'invoice',
    file:            'file',
    description:     'description',
    attachment_type: 'attachment_type',
  },
})

// -- User Settings ----------------------------------------------------------
export const userSettingsFields = createFieldMapper({
  UI_TO_API: {
    username:                    'username',
    email:                       'email',
    language:                    'language',
    timezone:                    'timezone',
    date_format:                 'date_format',
    email_notifications:         'email_notifications',
    notify_invoice_paid:         'notify_invoice_paid',
    notify_invoice_overdue:      'notify_invoice_overdue',
    default_currency:            'default_currency',
    default_payment_terms_days:  'default_payment_terms_days',
  },
})
