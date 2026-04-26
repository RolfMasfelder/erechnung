"""
Forms for the invoice_app application.
This module defines forms for creating and updating models.
"""

from django import forms

from invoice_app.models import BusinessPartner, Company, Invoice, InvoiceAttachment, InvoiceLine, Product


class CompanyForm(forms.ModelForm):
    """Form for creating and updating Company instances."""

    class Meta:
        model = Company
        fields = [
            "name",
            "legal_name",
            "tax_id",
            "vat_id",
            "commercial_register",
            "address_line1",
            "address_line2",
            "postal_code",
            "city",
            "state_province",
            "country",
            "phone",
            "fax",
            "email",
            "website",
            "bank_name",
            "bank_account",
            "iban",
            "bic",
            "default_currency",
            "default_payment_terms",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "legal_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(attrs={"class": "form-control"}),
            "vat_id": forms.TextInput(attrs={"class": "form-control"}),
            "commercial_register": forms.TextInput(attrs={"class": "form-control"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state_province": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "fax": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account": forms.TextInput(attrs={"class": "form-control"}),
            "iban": forms.TextInput(attrs={"class": "form-control"}),
            "bic": forms.TextInput(attrs={"class": "form-control"}),
            "default_currency": forms.TextInput(attrs={"class": "form-control"}),
            "default_payment_terms": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BusinessPartnerForm(forms.ModelForm):
    """Form for creating and updating BusinessPartner instances."""

    class Meta:
        model = BusinessPartner
        fields = [
            "is_customer",
            "is_supplier",
            "partner_type",
            "partner_number",
            "first_name",
            "last_name",
            "company_name",
            "legal_name",
            "tax_id",
            "vat_id",
            "commercial_register",
            "address_line1",
            "address_line2",
            "postal_code",
            "city",
            "state_province",
            "country",
            "phone",
            "fax",
            "email",
            "website",
            "payment_terms",
            "credit_limit",
            "preferred_currency",
            "contact_person",
            "accounting_contact",
            "accounting_email",
            "is_active",
        ]
        widgets = {
            "is_customer": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_supplier": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "partner_type": forms.Select(attrs={"class": "form-control"}),
            "partner_number": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "legal_name": forms.TextInput(attrs={"class": "form-control"}),
            "tax_id": forms.TextInput(attrs={"class": "form-control"}),
            "vat_id": forms.TextInput(attrs={"class": "form-control"}),
            "commercial_register": forms.TextInput(attrs={"class": "form-control"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state_province": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "fax": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "payment_terms": forms.NumberInput(attrs={"class": "form-control"}),
            "credit_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "preferred_currency": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "accounting_contact": forms.TextInput(attrs={"class": "form-control"}),
            "accounting_email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ProductForm(forms.ModelForm):
    """Form for creating and updating Product instances."""

    class Meta:
        model = Product
        fields = [
            "product_code",
            "name",
            "description",
            "product_type",
            "category",
            "subcategory",
            "brand",
            "manufacturer",
            "base_price",
            "currency",
            "cost_price",
            "list_price",
            "unit_of_measure",
            "weight",
            "dimensions",
            "tax_category",
            "default_tax_rate",
            "tax_code",
            "track_inventory",
            "stock_quantity",
            "minimum_stock",
            "barcode",
            "sku",
            "tags",
            "is_active",
            "is_sellable",
            "discontinuation_date",
        ]
        widgets = {
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "product_type": forms.Select(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "subcategory": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-control"}),
            "base_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "list_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_of_measure": forms.TextInput(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "dimensions": forms.TextInput(attrs={"class": "form-control"}),
            "tax_category": forms.Select(attrs={"class": "form-control"}),
            "default_tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tax_code": forms.TextInput(attrs={"class": "form-control"}),
            "track_inventory": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "stock_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "barcode": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_sellable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "discontinuation_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make inventory fields conditional
        if not self.instance.pk or not self.instance.track_inventory:
            self.fields["stock_quantity"].required = False
            self.fields["minimum_stock"].required = False


class InvoiceForm(forms.ModelForm):
    """Form for creating and updating Invoice instances."""

    # Backward compatibility: accept 'customer' field name, map to business_partner
    customer = forms.ModelChoiceField(
        queryset=BusinessPartner.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Invoice
        fields = [
            "invoice_number",
            "invoice_type",
            "company",
            "business_partner",
            "issue_date",
            "due_date",
            "delivery_date",
            "currency",
            "payment_terms",
            "payment_method",
            "payment_reference",
            "notes",
        ]
        widgets = {
            "invoice_number": forms.TextInput(attrs={"class": "form-control"}),
            "invoice_type": forms.Select(attrs={"class": "form-control"}),
            "company": forms.Select(attrs={"class": "form-control"}),
            "business_partner": forms.Select(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "delivery_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "payment_terms": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "payment_method": forms.TextInput(attrs={"class": "form-control"}),
            "payment_reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        """Map 'customer' field to 'business_partner' for backward compatibility."""
        cleaned_data = super().clean()
        # If customer is provided but business_partner is not, use customer
        if cleaned_data.get("customer") and not cleaned_data.get("business_partner"):
            cleaned_data["business_partner"] = cleaned_data["customer"]
        return cleaned_data

    def save(self, commit=True):
        """Ensure business_partner is set from customer field if needed."""
        instance = super().save(commit=False)
        # If customer was provided via form, ensure it's set to business_partner
        if self.cleaned_data.get("customer") and not instance.business_partner:
            instance.business_partner = self.cleaned_data["customer"]
        if commit:
            instance.save()
        return instance


class InvoiceLineForm(forms.ModelForm):
    """Form for creating and updating InvoiceLine instances."""

    class Meta:
        model = InvoiceLine
        fields = [
            "product",
            "description",
            "quantity",
            "unit_price",
            "unit_of_measure",
            "tax_rate",
            "discount_percentage",
            "discount_amount",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_of_measure": forms.TextInput(attrs={"class": "form-control"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "discount_percentage": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "discount_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active and sellable products
        self.fields["product"].queryset = Product.objects.filter(is_active=True, is_sellable=True)
        self.fields["product"].required = False

        # Add JavaScript to auto-populate fields when product is selected
        self.fields["product"].widget.attrs.update({"onchange": "populateFromProduct(this)"})


class InvoiceAttachmentForm(forms.ModelForm):
    """Form for creating and updating InvoiceAttachment instances."""

    class Meta:
        model = InvoiceAttachment
        fields = [
            "file",
            "description",
        ]
        widgets = {
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }
