# ADR 008: Error Handling & Validation Strategy

## Status

Accepted — zuletzt überprüft 14. März 2026

**Implementierungsstand:** Strategie vollständig umgesetzt. Layer 2 (DRF Exception Handler) weicht im Fehlerformat vom ursprünglichen Entwurf ab — tatsächliches Format siehe Abschnitt [Error Response Standardization](#error-response-standardization) unten.

## Context

The eRechnung system processes financial data that must be accurate, compliant with regulations, and properly validated. We need a consistent approach to:

1. **Input Validation**: When and where to validate user inputs
2. **Business Rule Validation**: How to implement and enforce business rules
3. **Error Reporting**: How to format and communicate errors to users and systems
4. **Validation Extensibility**: How to allow for new validation rules as requirements evolve

## Decision

**We will implement a layered validation approach with the following structure:**

### Layer 1: Client-Side Validation (UI/UX)
- **Purpose**: Immediate user feedback and improved user experience
- **Scope**: Basic format validation, required field checks, and simple business rules
- **Technology**: Vue.js 3 — Feldvalidierung in Komponenten, UI↔API-Feldnamen über `frontend/src/api/fieldMappings.js` (Anti-Corruption Layer)
- **Future Enhancement**: Rule engine for advanced UI/UX support to guide clients directly

### Layer 2: API Input Validation
- **Purpose**: Input sanitization and security validation
- **Scope**: Data type validation, format verification, and basic constraint checks
- **Technology**: Django REST Framework serializers and validators

### Layer 3: Domain Business Logic Validation
- **Purpose**: Complex business rules and ZUGFeRD compliance validation
- **Scope**: Invoice logic, tax calculations, and regulatory compliance
- **Technology**: Django model validation and custom business rule validators

### Layer 4: Database Constraints
- **Purpose**: Final data integrity safety net
- **Scope**: Referential integrity, unique constraints, and data consistency
- **Technology**: PostgreSQL constraints and triggers

## Rationale

The layered validation approach was chosen for the following reasons:

1. **Security**: Multiple validation layers prevent malicious data from reaching the database
2. **User Experience**: Immediate client-side feedback improves usability
3. **Performance**: Early validation reduces server load and improves response times
4. **Maintainability**: Clear separation of concerns makes validation logic easier to maintain
5. **Compliance**: Dedicated business logic layer ensures regulatory compliance
6. **Extensibility**: Future rule engine can enhance UI/UX without affecting core validation
7. **Robustness**: Multiple layers provide redundancy and catch edge cases

## Consequences

### Positive Consequences

- **Enhanced Security**: Multiple validation layers provide defense in depth
- **Better User Experience**: Immediate feedback reduces user frustration
- **Improved Performance**: Early validation reduces unnecessary processing
- **Clear Architecture**: Separation of concerns simplifies development and maintenance
- **Compliance Assurance**: Dedicated business logic validation ensures regulatory compliance
- **Future Flexibility**: Rule engine capability for advanced UI guidance

### Negative Consequences

- **Development Complexity**: Multiple validation layers require more initial development effort
- **Potential Redundancy**: Some validation logic may be duplicated across layers
- **Maintenance Overhead**: Changes to validation rules may require updates across multiple layers

### Mitigation Strategies

- **Shared Validation Rules**: Define common validation rules that can be used across layers
- **Comprehensive Documentation**: Clear documentation of validation responsibilities for each layer
- **Automated Testing**: Extensive testing to ensure validation consistency across layers
- **Rule Engine Planning**: Design current validation to accommodate future rule engine integration

## Implementation Details

### Layer 1: Client-Side Validation

```javascript
// Example client-side validation framework
const InvoiceValidation = {
    validateInvoiceNumber: (value) => {
        if (!value || value.length === 0) {
            return { valid: false, message: "Invoice number is required" };
        }
        if (!/^[A-Z0-9-]{3,20}$/.test(value)) {
            return { valid: false, message: "Invalid invoice number format" };
        }
        return { valid: true };
    },

    validateAmount: (value) => {
        if (isNaN(value) || value <= 0) {
            return { valid: false, message: "Amount must be a positive number" };
        }
        return { valid: true };
    }
};

// Future rule engine integration point
const RuleEngine = {
    // Placeholder for future advanced UI/UX guidance
    getFieldGuidance: (field, context) => {
        // Future implementation for intelligent form guidance
    }
};
```

### Layer 2: API Input Validation

```python
# Django REST Framework serializers
from rest_framework import serializers
from decimal import Decimal

class InvoiceSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(
        max_length=20,
        validators=[validate_invoice_number_format]
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01')
    )

    def validate(self, data):
        """Cross-field validation"""
        if data.get('due_date') < data.get('invoice_date'):
            raise serializers.ValidationError(
                "Due date cannot be before invoice date"
            )
        return data

def validate_invoice_number_format(value):
    """Custom validator for invoice number format"""
    import re
    if not re.match(r'^[A-Z0-9-]{3,20}$', value):
        raise serializers.ValidationError(
            "Invoice number must be 3-20 characters, alphanumeric and hyphens only"
        )
```

### Layer 3: Domain Business Logic Validation

```python
# Business rule validation
class InvoiceBusinessValidator:

    @staticmethod
    def validate_zugferd_compliance(invoice):
        """Validate ZUGFeRD Comfort Profile compliance"""
        errors = []

        # Required fields for Comfort Profile
        required_fields = [
            'invoice_number', 'invoice_date', 'seller_info',
            'buyer_info', 'currency', 'total_amount'
        ]

        for field in required_fields:
            if not getattr(invoice, field, None):
                errors.append(f"Required field '{field}' is missing")

        # Tax calculation validation
        calculated_tax = invoice.calculate_tax()
        if abs(calculated_tax - invoice.tax_amount) > Decimal('0.01'):
            errors.append("Tax calculation does not match provided tax amount")

        return errors

    @staticmethod
    def validate_business_rules(invoice):
        """Validate business-specific rules"""
        errors = []

        # Payment terms validation
        if invoice.payment_terms and invoice.payment_terms > 90:
            errors.append("Payment terms cannot exceed 90 days")

        # Credit limit check (future enhancement)
        # if invoice.buyer.credit_limit_exceeded(invoice.total_amount):
        #     errors.append("Invoice exceeds buyer's credit limit")

        return errors
```

### Layer 4: Database Constraints

```sql
-- PostgreSQL database constraints
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(20) NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount > 0),
    tax_amount DECIMAL(10,2) NOT NULL CHECK (tax_amount >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Business constraints
    CONSTRAINT valid_date_order CHECK (due_date >= invoice_date),
    CONSTRAINT valid_total CHECK (total_amount >= tax_amount),
    CONSTRAINT unique_invoice_number UNIQUE (invoice_number)
);

-- Audit trigger for validation failures
CREATE OR REPLACE FUNCTION audit_validation_failures()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        -- Log any constraint violations for analysis
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### Error Response Standardization

> **Hinweis:** Das ursprünglich geplante Format (`error: true`, `error_code`, `errors: []`, `timestamp`) wurde in der Implementierung durch ein kompakteres, verschachteltes Format ersetzt (siehe `invoice_app/api/exception_handlers.py`).

**Tatsächlich implementiertes Format** (alle API-Fehler):

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Benutzerfreundliche Fehlermeldung.",
        "details": {
            "field_name": ["Fehlermeldung 1", "Fehlermeldung 2"]
        }
    }
}
```

`details` ist optional und wird nur bei Validierungsfehlern (HTTP 400) mitgeliefert. Weitere Error-Codes: `NOT_FOUND`, `PERMISSION_DENIED`, `NOT_AUTHENTICATED`, `METHOD_NOT_ALLOWED`.

Implementierung: `invoice_app/api/exception_handlers.py` → `global_exception_handler()`

### Future Rule Engine Integration

```python
# Placeholder for future rule engine integration
class UIRuleEngine:
    """
    Future enhancement for intelligent UI/UX guidance
    This will provide dynamic form assistance and validation rules
    """

    def get_field_suggestions(self, field_name, current_context):
        """Provide intelligent suggestions based on context"""
        pass

    def get_validation_rules(self, form_type, user_context):
        """Dynamic validation rules based on user and context"""
        pass

    def get_help_text(self, field_name, user_experience_level):
        """Context-aware help text for better UX"""
        pass
```

## Testing Strategy

1. **Unit Tests**: Individual validation functions and rules
2. **Integration Tests**: Validation layer interactions
3. **End-to-End Tests**: Complete validation workflow testing
4. **Security Tests**: Validation bypass attempts and malicious input
5. **Performance Tests**: Validation impact on system performance

## Future Enhancements

1. **Rule Engine**: Advanced UI/UX guidance system for clients
2. **Machine Learning**: Pattern recognition for improved validation
3. **Custom Validation**: User-configurable business rules
4. **Integration Validation**: Third-party system compatibility checks

## References

- [Django Validation Framework](https://docs.djangoproject.com/en/stable/ref/validators/)
- [ZUGFeRD Validation Rules](https://www.ferd-net.de/zugferd/validation/index.html)
- [REST API Error Handling Best Practices](https://www.rfc-editor.org/rfc/rfc7807)
- [Client-Side Validation Best Practices](https://developer.mozilla.org/en-US/docs/Learn/Forms/Form_validation)
