import os, re, requests, json
from uuid import uuid4
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from ckeditor.fields import RichTextField
from app.models.company_info import Branch
from .log_connection import SyncSoftDeleteMixin
from django.core.validators import MinValueValidator
from app.utils.utils import OdooSync
from app.tasks import send_to_odoo_task
from django.utils import timezone

User = get_user_model()


def catalog_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("catalogs", filename)


def brand_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("brands", filename)


def product_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("products", filename)


def product_template_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("product-templates", filename)


def offer_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("offers", filename)

def partner_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("partners", filename)

class Brand(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name_uz = models.CharField(max_length=255, null=True, blank=True)
    name_ru = models.CharField(max_length=255, null=True, blank=True)
    name_en = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to=brand_upload_to, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_top = models.BooleanField(default=False)

    def __str__(self):
        return (
            (self.name_uz or "").strip()
            or (self.name_ru or "").strip()
            or (self.name_en or "").strip()
            or "No brand name"
        )

    def prepare_odoo_data(self):
        return OdooSync.prepare_brand_data(self)


class Category(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name_uz = models.CharField(max_length=255, null=True, blank=True)
    name_ru = models.CharField(max_length=255, null=True, blank=True)
    name_en = models.CharField(max_length=255, null=True, blank=True)

    # for a system of linked multiple categories
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    mxik = models.CharField(max_length=255)
    package_code = models.CharField(max_length=255)
    image = models.ImageField(upload_to=catalog_upload_to, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_visible = models.BooleanField(default=True, help_text="Is this category visible on the website?")

    def __str__(self):
        return (
            (self.name_uz or "").strip()
            or (self.name_ru or "").strip()
            or (self.name_en or "").strip()
            or "No name in any language"
        )

    @property
    def depth(self):
        level = 0
        p = self.parent
        while p:
            level += 1
            p = p.parent
        return level

    def clean(self):
        if self.depth > 1:
            raise ValidationError(_("Category depth must be <= 2"))
        if self.parent and self.parent.product_templates.exists():
            raise ValidationError(
                _("Cannot add subcategory to a category that has products")
            )

    def prepare_odoo_data(self):
        return OdooSync.prepare_category_data(self)


class ProductTemplate(SyncSoftDeleteMixin):
    PRODUCT_TYPES = [
        ("CASHBACK", _("Cashback")),
        ("PRODUCT", _("Product")),
        ("DELIVERY_PRICE", _("Delivery Price")),
        ("COUPON", _("Coupon")),
    ]
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    on_hand = models.FloatField(default=0.00)
    description = RichTextField(default="No description provided", blank=True, null=True)
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default="PRODUCT",
        help_text="Type of product (e.g., cashback, product, delivery price, coupon)",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_templates",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_templates",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_templates",
    )
    url = models.URLField(
        max_length=500, null=True, blank=True, help_text="Product URL on website"
    )

    is_top = models.BooleanField(default=False, help_text="Is this product top rated?")
    is_visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} - {self.name}"
    class Meta:
        ordering = ["-id"]

    def clean(self):
        if self.category and self.category.category_set.exists():
            raise ValidationError(
                _(
                    "Product can only be assigned to a leaf category (one that has no subcategories)."
                )
            )

    def prepare_odoo_data(self):
        return OdooSync.prepare_product_template_data(self)

    @property
    def single_product_id(self):
        return self.products.first().id if self.products.count() == 1 else None

    def _slugify(self, text):
        slug = text.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = re.sub(r"^-|-$", "", slug)
        return slug

    def save(self, *args, **kwargs):
        if self.id:
            slug = self._slugify(self.name)
            self.url = f"https://car-land.uz/products/{self.id}-{slug}"
        super().save(*args, **kwargs) 


class ProductTemplateImage(SyncSoftDeleteMixin):
    product_template = models.ForeignKey(
        ProductTemplate, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to=product_template_upload_to, null=True, blank=True
    )
    odoo_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Image for {self.product_template.name}"
    def prepare_odoo_data(self):
       return OdooSync.prepare_template_image(self)


class Variant(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def prepare_odoo_data(self):
        return OdooSync.prepare_variant_data(self)


class Option(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="variant_option"
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.variant.name} - {self.name}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_option_data(self)


class ProductOption(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    product_template = models.ForeignKey(
        ProductTemplate, on_delete=models.CASCADE, related_name="product_options"
    )
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name="product_option"
    )
    additional_price = models.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    product_template_attribute_line = models.ForeignKey(
        "ProductVariants",
        on_delete=models.CASCADE,
        related_name="product_varialts_line",
    )

    def __str__(self):
        return f"{self.odoo_id}"

    def prepare_odoo_data(self):
        return OdooSync.perpare_product_option_data(self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        related_products = Product.objects.filter(
            product_template=self.product_template, attributes=self.option
        )
        for product in related_products:
            product.price = product.calculate_price()
            product.save()


class ProductVariants(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="product_template_variants"
    )
    product_template = models.ForeignKey(
        ProductTemplate,
        on_delete=models.CASCADE,
        related_name="product_template_options",
    )
    product_options = models.ManyToManyField(
        Option, related_name="variant_product_options"
    )

    def __str__(self):
        return f"Variand #{self.id} with product template {self.product_template.name}"

    """
    Bundagi variant va option moslik tekshiruvini serializerga kochirish kera
    """

    # def clean(self):
    #     invalid_options = [
    #         option for option in self.product_options.all()
    #         if option.variant != self.variant
    #     ]
    #     if invalid_options:
    #         raise ValidationError(
    #             f"Cannot save: The following product options are not related to variant '{self.variant.name}': "
    #             f"{', '.join(str(opt) for opt in invalid_options)}"
    #         )
    def prepare_odoo_data(self):
        return OdooSync.perpare_product_variant_data(self)


class Product(SyncSoftDeleteMixin):
    PRODUCT_TYPES = [
        ("CASHBACK", _("Cashback")),
        ("PRODUCT", _("Product")),
        ("DELIVERY_PRICE", _("Delivery Price")),
        ("COUPON", _("Coupon")),
    ]
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    product_template = models.ForeignKey(
        ProductTemplate, on_delete=models.CASCADE, related_name="products"
    )
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default="PRODUCT",
        help_text="Type of product (e.g., cashback, product, delivery price, coupon)",
    )
    attributes = models.ManyToManyField(Option, blank=True)
    description = RichTextField(
        null=True,
        blank=True,
        help_text="Product description (If empty, the product template description will be used)",
    )
    image = models.ImageField(
        upload_to=product_upload_to,
        null=True,
        blank=True,
        help_text="Product image (If empty, the product template image will be used)",
    )
    price = models.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    free_quantity = models.FloatField(default=0.00)
    mxik = models.CharField(max_length=255, null=True, blank=True)
    package_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_top = models.BooleanField(default=False)

    def calculate_price(self, attributes=None):
        if not self.product_template:
            return self.price

        # Agar atributlar tashqaridan berilmagan bo‘lsa, bazadan o‘qiladi
        if attributes is None:
            if not self.pk:
                return self.product_template.price
            attributes = self.attributes.all()

        product_options = ProductOption.objects.filter(
            product_template=self.product_template, option__in=attributes
        )
        total_additional_price = sum(
            option.additional_price for option in product_options
        )
        return self.product_template.price + total_additional_price

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = (
                self.product_template.name if self.product_template else "Product"
            )

        if self.product_template:
            self.product_type = self.product_template.product_type

        if not self.description:
            self.description = (
                self.product_template.description
                if self.product_template
                else "No description provided"
            )

        image = (
            self.product_template.images.first().image
            if self.product_template and self.product_template.images.exists()
            else None
        )

        if not self.image:
            self.image = image

        # if not self.mxik:
        #     self.mxik = (
        #         self.product_template.category.mxik
        #         if self.product_template and self.product_template.category
        #         else ""
        #     )

        # if not self.package_code:
        #     self.package_code = (
        #         self.product_template.category.package_code
        #         if self.product_template and self.product_template.category
        #         else ""
        #     )

        self.price = self.calculate_price()
        super().save(*args, **kwargs) 

    def __str__(self):
        return f"product #{self.id} with product template {self.product_template.name}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_product_data(self)


class ProductRating(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="product_reviews"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="ratings"
    )
    rating = models.IntegerField()
    anonymous = models.BooleanField(
        default=False, help_text="If True, the review will be anonymous"
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from app.models.order import Order

        super().clean()
        has_completed_order = Order.objects.filter(
            user=self.reviewer, status="COMPLETED", items__product=self.product
        ).exists()
        if not has_completed_order:
            raise ValidationError(
                "You can only review products you have completed orders for."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reviewer} - {self.product} - {self.rating}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_product_rating(self)


class Currency(models.Model):
    """Model representing a currency (similar to Odoo's res.currency)"""

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=50)
    code = models.CharField(
        max_length=3, unique=True, help_text="ISO 4217 currency code (e.g. USD, EUR)"
    )
    symbol = models.CharField(max_length=5)
    rounding = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0.01,
        validators=[MinValueValidator(0)],
        help_text="Rounding factor for this currency (e.g. 0.01 for cents)",
    )
    active = models.BooleanField(default=True)
    decimal_places = models.PositiveSmallIntegerField(
        default=2, help_text="Number of decimal places to display (usually 2)"
    )

    class Meta:
        verbose_name_plural = "Currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def prepare_odoo_data(self):
        return OdooSync.prepare_currency_data(self)


class Pricelist(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="pricelists",
        null=True,
        blank=True,
    )
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    def prepare_odoo_data(self):
        return OdooSync.prepare_pricelist_data(self)


class Discount(SyncSoftDeleteMixin):
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    pricelist = models.ForeignKey(
        Pricelist, on_delete=models.CASCADE, related_name="items", null=True, blank=True
    )
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="percentage"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="discounts",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="discounts",
        null=True,
        blank=True,
    )
    product_template = models.ForeignKey(
        ProductTemplate,
        on_delete=models.CASCADE,
        related_name="discounts",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="discounts",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="discounts", null=True, blank=True
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    percent = models.FloatField(null=True, blank=True)
    min_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    max_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    time_from = models.DateTimeField(null=True, blank=True)
    time_to = models.DateTimeField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.amount}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_discount_data(self)

    # def clean(self):
    #     super().clean()
    #     fields = {
    #         'category': self.category,
    #         'template': self.product_template,
    #         'product': self.product,
    #         'branch': self.branch,
    #         'all': None
    #     }

    #     for key, field_value in fields.items():
    #         if self.apply_on == key:
    #             if key != 'all' and not field_value:
    #                 raise ValidationError({key: _(f"{key.title()} must be selected when apply_on is '{key}'")})
    #         else:
    #             if field_value:
    #                 raise ValidationError({key: _(f"{key.title()} must be empty when apply_on is '{self.apply_on}'")})


class SavedProduct(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_products"
    )
    product_template = models.ForeignKey(
        ProductTemplate,
        on_delete=models.CASCADE,
        related_name="saved_products",
        null=True,
        blank=True,
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.info.first_name} saved {self.product_template.name} at {self.saved_at}"


class Offer(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    title_uz = models.CharField(max_length=255, null=True, blank=True)
    title_en = models.CharField(max_length=255, null=True, blank=True)
    title_ru = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to=offer_upload_to)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description_uz = RichTextField(
        null=True, blank=True, help_text="Offer description in Uzbek"
    )
    description_en = RichTextField(
        null=True, blank=True, help_text="Offer description in English"
    )
    description_ru = RichTextField(
        null=True, blank=True, help_text="Offer description in Russian"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Offer #{self.id} From {self.start_date} To {self.end_date}"

    def clean(self):
        super().clean()
        # if self.start_date and self.end_date and self.start_date >= self.end_date:
        #     raise ValidationError(
        #         {"end_date": _("The end date must be later than the start date.")}
        #     )
        if not any([self.title_uz, self.title_en, self.title_ru]):
            raise ValidationError(
                {"title_uz": _("At least one title (uz, en, ru) must be provided.")}
            )


class WareHouse(SyncSoftDeleteMixin):
    """
    Warehouse model that syncs with Odoo's stock.warehouse
    """

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouses",
    )
    active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    def prepare_odoo_data(self):
        return OdooSync.prepare_wareHouse_data(self)


class Location(SyncSoftDeleteMixin):
    """
    Location model that syncs with Odoo's stock.location
    """

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    complete_name = models.CharField(max_length=255)
    location_type = models.CharField(
        max_length=20,
        choices=[
            ("view", "View"),
            ("internal", "Internal"),
            ("customer", "Customer"),
            ("inventory", "Inventory"),
            ("production", "Production"),
            ("supplier", "Supplier"),
            ("transit", "Transit"),
        ],
    )
    warehouse = models.ForeignKey(
        WareHouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="locations",
    )
    parent_location = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="child_locations",
    )
    active = models.BooleanField(default=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="branch_locations",
        null=True,
        blank=True,
    )
    last_sync = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.complete_name

    def prepare_odoo_data(self):
        return OdooSync.prepare_location_data(self)


class StockQuant(SyncSoftDeleteMixin):
    """
    Stock quantity model that syncs with Odoo's stock.quant
    """

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_quants"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="stock_quants_branch"
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="stock_quants"
    )
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    last_sync = models.DateTimeField(null=True, blank=True)
    in_date = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.product} at {self.location}: {self.quantity}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_stuck_quant_data(self)

    def save(self, *args, **kwargs):
        if self.location and self.location.branch:
            self.branch = self.location.branch
        elif not self.branch:  # Agar branch aniqlanmagan bo'lsa
            raise ValueError("Branch must be set either directly or through location")
        product = self.product
        product.free_quantity = self.quantity-self.reserved_quantity
        product.send_odoo = False
        product.save()
        return super().save(*args, **kwargs)


class OilBrand(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (self.name or "").strip() or "No brand name"

    def prepare_odoo_data(self):
        return OdooSync.prepare_oil_brand_data(self)


class FilterBrand(SyncSoftDeleteMixin):
    name = models.CharField(max_length=255)

    def __str__(self):
        return (self.name or "").strip() or "No brand name"

    def prepare_odoo_data(self):
        return OdooSync.prepare_filter_brand_data(self)

class Partner(SyncSoftDeleteMixin):
    picture = models.ImageField(
        upload_to=partner_upload_to, null=True, blank=True
    )

    name_en = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_uz = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_en or "Unnamed Partner"