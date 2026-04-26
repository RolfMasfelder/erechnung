# ADR 003: Use Python-based Tools for PDF/A Generation

## Status

**Superseded by [ADR-023](ADR-023-pypdf-only-backend.md)** (September 2025)

Dieses ADR ist nicht mehr gültig. Die ursprüngliche Entscheidung wählte eine Kombination aus ReportLab, WeasyPrint und factur-x. In der Praxis wurde die Implementierung auf `pypdf` + `factur-x` konsolidiert (PyPDF4 wurde abgelöst, ReportLab entfernt). Alle Details zur aktuellen Entscheidung stehen in ADR-023.

## Context

The eRechnung system requires generation of PDF/A-3 documents with embedded ZUGFeRD XML data. We need a reliable, standards-compliant solution that:
- Creates PDF/A-3 compliant documents
- Allows embedding XML files according to ZUGFeRD specifications
- Integrates well with our Django application
- Is maintainable and extendable
- Provides good performance

## Decision

We will use Python-based tools for PDF/A-3 generation, specifically a combination of:
- ReportLab for PDF generation
- factur-x library for ZUGFeRD XML embedding
- WeasyPrint for HTML-to-PDF conversion when needed

## Rationale

- **Ecosystem Integration**: Python-based tools integrate naturally with our Django application, avoiding cross-language communication overhead.

- **Factur-X Library**: The factur-x Python library is specifically designed for creating ZUGFeRD-compliant invoices and handles the complexities of embedding XML in PDF/A-3.

- **ReportLab Maturity**: ReportLab is a mature, well-tested library for PDF generation in Python with extensive documentation and community support.

- **WeasyPrint Flexibility**: WeasyPrint allows for HTML-to-PDF conversion, which simplifies template-based document generation and styling using CSS.

- **Maintainability**: Using Python throughout the stack simplifies maintenance and reduces the need for specialized knowledge in multiple programming languages.

- **Control and Customization**: Python-based tools offer fine-grained control over PDF generation, allowing us to implement custom requirements and ensure standards compliance.

- **Open Source**: These tools are open-source, reducing licensing costs and vendor lock-in.

## Consequences

### Positive

- Simplified architecture with a single language stack
- Easier integration with Django models and templates
- More control over the PDF generation process
- Reduced deployment complexity
- Easier to find developers with Python skills

### Negative

- May require more custom code compared to specialized PDF/A solutions
- Performance may be slower compared to some native or compiled solutions
- May require additional testing to ensure PDF/A-3 compliance

### Risks

- Need to ensure all PDF/A-3 requirements are met
- May need to handle memory usage carefully for large batches of documents
- Potential for upgrades to break compatibility

## Alternatives Considered

- **Java-based PDF/A generation**: Initially considered for its maturity in the PDF/A space, but rejected due to the added complexity of cross-language integration and deployment.

- **Commercial PDF libraries**: Evaluated but rejected due to licensing costs and potential vendor lock-in.

## References

- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [factur-x Python Library](https://github.com/invoice-x/factur-x)
- [WeasyPrint Documentation](https://weasyprint.readthedocs.io/)
