/**
 * UN/CEFACT Maßeinheiten
 *
 * value:  Interne numerische ID – wird in der DB und über die API übertragen.
 * label:  Deutsche Bezeichnung für die Oberfläche.
 *
 * Übersetzung ID → UN/CEFACT-Code (für ZUGFeRD-XML) erfolgt serverseitig
 * via Product.UNIT_UNCEFACT_CODES.
 */
export const UNIT_OPTIONS = [
  { value: 1, label: 'Stück' },
  { value: 2, label: 'Stunde' },
  { value: 3, label: 'Tag' },
  { value: 4, label: 'Kilogramm' },
  { value: 5, label: 'Liter' },
  { value: 6, label: 'Monat' },
]

const UNIT_LABEL_MAP = Object.fromEntries(UNIT_OPTIONS.map(o => [o.value, o.label]))

/**
 * Gibt den deutschen Anzeigetext für eine Einheiten-ID zurück.
 * Falls die ID unbekannt ist, wird sie als Fallback direkt zurückgegeben.
 */
export function formatUnitLabel(id) {
  if (id === null || id === undefined || id === '') return '-'
  return UNIT_LABEL_MAP[id] ?? String(id)
}
