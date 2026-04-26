from lxml import etree


# XML-Dokument laden
xml_doc = etree.parse("invoice.xml")

# --- XSD-Validierung ---
with open("invoice.xsd", "rb") as f:
    xsd_doc = etree.parse(f)
xmlschema = etree.XMLSchema(xsd_doc)
if xmlschema.validate(xml_doc):
    print("XSD-Validierung erfolgreich!")
else:
    print("XSD-Validierung fehlgeschlagen!")
    print(xmlschema.error_log)

# --- Schematron-Validierung ---
# Schematron-Dokument laden (direkt, wenn lxml-Schematron unterstützt wird)
with open("invoice.sch", "rb") as f:
    schematron_doc = etree.parse(f)
schematron = etree.Schematron(schematron_doc)
if schematron.validate(xml_doc):
    print("Schematron-Validierung erfolgreich!")
else:
    print("Schematron-Validierung fehlgeschlagen!")
    for error in schematron.error_log:
        print(error.message)
