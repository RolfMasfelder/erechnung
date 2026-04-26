import apiClient from '../client'

/**
 * Import Service
 * Handles bulk import of business partners and products
 */
export const importService = {
  /**
   * Import business partners (customers/suppliers)
   * @param {Array} rows - Array of partner data objects
   * @param {Object} options - Import options
   * @param {boolean} options.skipDuplicates - Skip duplicate entries (default: true)
   * @param {boolean} options.updateExisting - Update existing records (default: false)
   * @returns {Promise<Object>} Import result with counts and errors
   */
  async importBusinessPartners(rows, options = {}) {
    const response = await apiClient.post('/business-partners/import/', {
      rows,
      skip_duplicates: options.skipDuplicates ?? true,
      update_existing: options.updateExisting ?? false
    })
    return response.data
  },

  /**
   * Import products
   * @param {Array} rows - Array of product data objects
   * @param {Object} options - Import options
   * @param {boolean} options.skipDuplicates - Skip duplicate entries (default: true)
   * @param {boolean} options.updateExisting - Update existing records (default: false)
   * @returns {Promise<Object>} Import result with counts and errors
   */
  async importProducts(rows, options = {}) {
    const response = await apiClient.post('/products/import/', {
      rows,
      skip_duplicates: options.skipDuplicates ?? true,
      update_existing: options.updateExisting ?? false
    })
    return response.data
  },

  /**
   * Map CSV headers to API field names for business partners
   * Handles common German column names
   */
  mapBusinessPartnerHeaders(headers) {
    const headerMap = {
      // German -> API field name
      'Firmenname': 'company_name',
      'Firma': 'company_name',
      'Name': 'company_name',
      'name': 'company_name',
      'Adresse': 'address_line1',
      'Straße': 'address_line1',
      'Strasse': 'address_line1',
      'street': 'address_line1',
      'Adresszeile 1': 'address_line1',
      'Adresszeile 2': 'address_line2',
      'PLZ': 'postal_code',
      'Postleitzahl': 'postal_code',
      'Ort': 'city',
      'Stadt': 'city',
      'Land': 'country_code',
      'Ländercode': 'country_code',
      'Steuernummer': 'tax_id',
      'USt-IdNr': 'vat_id',
      'USt-IdNr.': 'vat_id',
      'Umsatzsteuer-ID': 'vat_id',
      'Telefon': 'phone',
      'Tel': 'phone',
      'Fax': 'fax',
      'E-Mail': 'email',
      'Email': 'email',
      'Webseite': 'website',
      'Homepage': 'website',
      'Ansprechpartner': 'contact_person',
      'Zahlungsziel': 'payment_terms',
      'Zahlungsziel (Tage)': 'payment_terms',
      'Kreditlimit': 'credit_limit',
      'Währung': 'preferred_currency',
      'Kundennummer': 'partner_number',
      'Partnernummer': 'partner_number',
      'Aktiv': 'is_active',
      'Ist Kunde': 'is_customer',
      'Ist Lieferant': 'is_supplier'
    }

    return headers.map(h => headerMap[h] || h.toLowerCase().replace(/[^a-z0-9]/g, '_'))
  },

  /**
   * Map CSV headers to API field names for products
   * Handles common German column names
   */
  mapProductHeaders(headers) {
    const headerMap = {
      // German -> API field name
      'Produktname': 'name',
      'Name': 'name',
      'Bezeichnung': 'name',
      'Artikelnummer': 'product_code',
      'Artikelnr': 'product_code',
      'Produktcode': 'product_code',
      'SKU': 'product_code',
      'Beschreibung': 'description',
      'Kurzbeschreibung': 'short_description',
      'Kategorie': 'category',
      'Unterkategorie': 'subcategory',
      'Marke': 'brand',
      'Hersteller': 'manufacturer',
      'Preis': 'base_price',
      'Grundpreis': 'base_price',
      'VK-Preis': 'base_price',
      'Verkaufspreis': 'base_price',
      'Einkaufspreis': 'cost_price',
      'EK-Preis': 'cost_price',
      'Einheit': 'unit_of_measure',
      'Mengeneinheit': 'unit_of_measure',
      'MwSt-Satz': 'tax_rate',
      'Steuersatz': 'tax_rate',
      'Steuerkategorie': 'tax_category',
      'Währung': 'currency',
      'Lagerbestand': 'stock_quantity',
      'Bestand': 'stock_quantity',
      'Meldebestand': 'reorder_level',
      'Aktiv': 'is_active',
      'Verkäuflich': 'is_sellable',
      'Lager verfolgen': 'track_inventory'
    }

    return headers.map(h => headerMap[h] || h.toLowerCase().replace(/[^a-z0-9]/g, '_'))
  },

  /**
   * Transform parsed CSV data to API format for business partners
   * @param {Array} data - Parsed CSV data with original headers
   * @param {Array} originalHeaders - Original CSV headers
   * @returns {Array} Transformed data with API field names
   */
  transformBusinessPartnerData(data, originalHeaders) {
    const mappedHeaders = this.mapBusinessPartnerHeaders(originalHeaders)

    return data.map(row => {
      const transformed = {}
      originalHeaders.forEach((header, idx) => {
        const apiField = mappedHeaders[idx]
        let value = row[header]

        // Handle boolean fields
        if (['is_active', 'is_customer', 'is_supplier'].includes(apiField)) {
          value = this.parseBoolean(value)
        }
        // Handle numeric fields
        else if (['payment_terms'].includes(apiField)) {
          value = parseInt(value, 10) || 30
        }
        else if (['credit_limit'].includes(apiField)) {
          value = this.parseGermanDecimal(value)
        }

        transformed[apiField] = value
      })
      return transformed
    })
  },

  /**
   * Parse German decimal format (1.234,56 → 1234.56)
   * German uses dot as thousand separator and comma as decimal separator
   */
  parseGermanDecimal(value) {
    if (!value || typeof value !== 'string') return value ? parseFloat(value) : null
    // Remove thousand separators (dots), then replace decimal comma with dot
    return parseFloat(value.replace(/\./g, '').replace(',', '.'))
  },

  /**
   * Transform parsed CSV data to API format for products
   * @param {Array} data - Parsed CSV data with original headers
   * @param {Array} originalHeaders - Original CSV headers
   * @returns {Array} Transformed data with API field names
   */
  transformProductData(data, originalHeaders) {
    const mappedHeaders = this.mapProductHeaders(originalHeaders)

    return data.map(row => {
      const transformed = {}
      originalHeaders.forEach((header, idx) => {
        const apiField = mappedHeaders[idx]
        let value = row[header]

        // Handle boolean fields
        if (['is_active', 'is_sellable', 'track_inventory'].includes(apiField)) {
          value = this.parseBoolean(value)
        }
        // Handle numeric fields
        else if (['stock_quantity', 'reorder_level'].includes(apiField)) {
          value = parseInt(value, 10) || 0
        }
        else if (['base_price', 'cost_price', 'tax_rate'].includes(apiField)) {
          value = this.parseGermanDecimal(value)
        }

        transformed[apiField] = value
      })
      return transformed
    })
  },

  /**
   * Parse various boolean representations
   */
  parseBoolean(value) {
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') {
      const lower = value.toLowerCase().trim()
      return ['true', '1', 'ja', 'yes', 'x', 'aktiv', 'active'].includes(lower)
    }
    return Boolean(value)
  }
}
