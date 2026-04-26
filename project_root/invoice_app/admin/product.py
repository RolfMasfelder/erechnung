"""Admin configuration for Product model."""

from django.contrib import admin

from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import Product


@admin.register(Product)
class ProductAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for Product model with inventory tracking."""

    list_display = (
        "product_code",
        "name",
        "product_type",
        "category",
        "base_price",
        "currency",
        "default_tax_rate",
        "is_active",
        "is_sellable",
    )
    search_fields = ("product_code", "name", "description", "category", "brand", "manufacturer")
    list_filter = ("product_type", "category", "tax_category", "is_active", "is_sellable", "track_inventory")
    list_editable = ("base_price", "is_active", "is_sellable")
    readonly_fields = ("created_at", "updated_at", "profit_margin", "is_in_stock", "needs_restock")
    autocomplete_fields = ("created_by",)

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("product_code", "name", "description", "product_type", "is_active", "is_sellable")},
        ),
        ("Categorization", {"fields": ("category", "subcategory", "brand", "manufacturer", "tags")}),
        ("Pricing", {"fields": ("base_price", "currency", "cost_price", "list_price")}),
        ("Units & Measurements", {"fields": ("unit_of_measure", "weight", "dimensions")}),
        ("Tax Information", {"fields": ("tax_category", "default_tax_rate", "tax_code")}),
        ("Inventory", {"fields": ("track_inventory", "stock_quantity", "minimum_stock"), "classes": ("collapse",)}),
        ("Additional Details", {"fields": ("barcode", "sku", "discontinuation_date"), "classes": ("collapse",)}),
        ("System Information", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        """Add computed fields to readonly when editing existing object."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(["profit_margin", "is_in_stock", "needs_restock"])
        return readonly

    def profit_margin(self, obj):
        """Display profit margin percentage."""
        if obj.profit_margin is not None:
            return f"{obj.profit_margin:.2f}%"
        return "N/A"

    profit_margin.short_description = "Profit Margin"

    def is_in_stock(self, obj):
        """Display stock status indicator."""
        if not obj.track_inventory:
            return "N/A"
        return "✓" if obj.is_in_stock else "✗"

    is_in_stock.short_description = "In Stock"
    is_in_stock.boolean = True

    def needs_restock(self, obj):
        """Display restock warning indicator."""
        if not obj.track_inventory:
            return "N/A"
        return "⚠" if obj.needs_restock else "✓"

    needs_restock.short_description = "Needs Restock"
