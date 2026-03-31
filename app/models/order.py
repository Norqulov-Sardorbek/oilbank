from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from .company_info import Branch
from django.utils.translation import gettext_lazy as _
from app.models.product import Product, Category
from uuid import uuid4
import os


User = get_user_model()
from .log_connection import SyncSoftDeleteMixin
from app.utils.utils import OdooSync


def rating_image_file_path(instance, filename) -> str:
    """
    This function generates a name for saving the
    card image and creates a path to the appropriate folder.
    """
    extention = str(filename).split(".")[-1]
    new_filename = f"{filename}-{uuid4()}.{extention}"
    return os.path.join("rating-images/", new_filename)


class RatingType(SyncSoftDeleteMixin):
    class Status(models.TextChoices):
        BAD = "bad", _("Bad")
        GOOD = "good", _("Good")

    icon = models.FileField(upload_to=rating_image_file_path)
    name_en = models.CharField()
    name_ru = models.CharField()
    name_uz = models.CharField()
    status = models.CharField(
        max_length=255,
        choices=Status.choices,
        default=Status.GOOD,
        null=True,
        blank=True,
    )

    def prepare_odoo_data(self):
        return OdooSync.prepate_rating(self)


class Region(SyncSoftDeleteMixin):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_region_data(self)


class District(SyncSoftDeleteMixin):
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.region.name})"

    def prepare_odoo_data(self):
        return OdooSync.prepare_district_data(self)


class DeliveryPrice(SyncSoftDeleteMixin):
    district = models.OneToOneField(
        District, on_delete=models.CASCADE, related_name="delivery_prices_destrict"
    )
    price = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.district.name} - {self.price}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_delivery_price_data(self)


class Order(SyncSoftDeleteMixin):
    PAYMENT_STATUS_CHOICES = [
        ("DRAFT", _("Draft")),
        ("PENDING", _("Pending")),
        ("COMPLETED", _("Completed")),
        ("REFAUND", _("Refaund")),
        ("FAILED", _("Failed")),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("CASH", _("Cash")),
        ("CLICK", _("Click")),
        ("CARD", _("Card")),
        ("PAYME", _("Payme")),
        ("UZUM", _("Uzum")),
        ("MULTICARD", _("Multicard")),
        ("XAZNA", _("Xazna")),
        ("ALIF", _("Alif")),
        ("BEEPUL", _("Beepul")),
        ("ANORBANK", _("Anorbank")),
        ("OSON", _("Oson")),
        ("ON_RECEIVE", _("On Receive")),
        ("CASHBACK", _("Cashback")),
        ("MIXED", _("Mixed")),
    ]

    TYPE_CHOICES = [
        ("DELIVERY", _("Delivery")),
        ("PICKUP", _("Pickup")),
    ]

    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("PROCESSING", _("Processing")),
        ("COLLECTING", _("Collecting")),
        ("READY", _("Ready for shipment")),
        # ("OUT_FOR_DELIVERY", _("Out for delivery")),
        ("COMPLETED", _("Completed")),
        ("CANCELLED", _("Cancelled")),
    ]

    SOURCE_CHOICES = [
        ("WEB", _("Web")),
        ("MOBILE", _("Mobile")),
        ("TG_MINI_APP", _("Telegram Mini App")),
    ]
    name = models.CharField(max_length=255,null=True,blank=True)
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    car = models.ForeignKey(
        "app.Car",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    uuid = models.UUIDField(
        default=uuid4, editable=False, unique=True, null=True, blank=True
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.0, help_text="Total price of the order"
    )
    discount_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.0, help_text="Total discount amount applied to the order"
    )
    total_items_count = models.PositiveIntegerField(
        default=0, help_text="Total number of order items (for sync tracking)"
    )

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="WEB")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)  # Added default
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    address_id = models.ForeignKey(
        "user.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    description = models.TextField(null=True, blank=True)
    promocode_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.0,
        help_text="Promocode amount applied to this order",
    )
    promocode = models.ForeignKey(
        "app.PromoCode",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="order",
    )
    pricelist = models.ForeignKey(
        "app.Pricelist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
    )
    pickup_time = models.DateTimeField(null=True, blank=True)
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    raxmat_reference = models.CharField(max_length=255, null=True, blank=True)
    raxmat_payment_id = models.CharField(max_length=255, null=True, blank=True)
    fiscal_url = models.CharField(max_length=255, null=True, blank=True)
    f_num = models.CharField(max_length=255, null=True, blank=True)
    fm_num = models.CharField(max_length=255, null=True, blank=True)
    balance_percentage = models.IntegerField(default=0)
    payment_time = models.DateTimeField(null=True, blank=True, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    cancelled_at = models.DateTimeField(null=True, blank=True, editable=False)
    balance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    order_reference = models.CharField(max_length=255, null=True, blank=True)
    card_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    cash_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    balance_status_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the balance status at order creation",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        from django.conf import settings

        MAX_ORDER_AMOUNT = Decimal(str(settings.MAX_ORDER_AMOUNT))

        super().clean()
        if self.price is None:
            raise ValidationError(
                _("Price cannot be None"),
                code="invalid",
            )
        if self.price > MAX_ORDER_AMOUNT:
            raise ValidationError(
                _("Order amount exceeds the maximum limit of %(max_amount)s"),
                params={"max_amount": MAX_ORDER_AMOUNT},
                code="invalid",
            )
        if self.status == "COMPLETED" and self.payment_status != "COMPLETED":
            raise ValidationError(
                _("Order status cannot be COMPLETED without payment status being COMPLETED"),
                code="invalid",
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == "COMPLETED" and self.completed_at is None:
            self.completed_at = now()
        if self.status == "CANCELLED" and self.cancelled_at is None:
            self.cancelled_at = now()
        super().save(*args, **kwargs)
        self.create_check()

    def __str__(self):
        return f"Order {self.id} - {self.user}"

    def create_check(self):
        from .card import get_or_create_check_for_order
        """
        Instance method to create a check for this order if payment is completed.
        Add this method to the Order model class.
        """
        return get_or_create_check_for_order(self)
    
    def prepare_odoo_data(self):
        return OdooSync.prepare_order_data(self)


class OrderItem(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_item",
    )
    sended_to_odoo = models.BooleanField(default=False)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=14, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.0,
        help_text="Discount amount applied to this item",
    )
    discount_percent = models.FloatField(
        default=0.0, help_text="Discount percentage applied to this item"
    )

    def __str__(self):
        return f"{self.product} - {self.quantity} pcs"

    def prepare_odoo_data(self):
        return OdooSync.prepare_order_line_data(self)


class OrderRating(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="ratings")
    rating = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    options_ids = models.ManyToManyField(RatingType, related_name="order_options")

    def __str__(self):
        return f"Rating {self.rating} by {self.reviewer}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_order_rating(self)


class Basket(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="baskets")
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"Basket {self.id} - {self.user}"

    def update_total(self):
        """Update and save the total price"""
        self.price = sum(item.total_price for item in self.items.all())
        self.save()


class BasketItem(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="basket_item",
    )
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=14, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.0,
        help_text="Discount amount applied to this item",
    )
    discount_percent = models.FloatField(
        default=0.0, help_text="Discount percentage applied to this item"
    )

    def save(self, *args, **kwargs):
        if self.product:
            self.price = self.product.price
        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)
        self.basket.update_total()

    def __str__(self):
        return f"{self.product} - {self.quantity} pcs"

    class Meta:
        ordering = ["-id"]


class LoyaltyProgram(SyncSoftDeleteMixin):
    name = models.CharField(max_length=255, default="No name")
    program_type = models.CharField(max_length=20, choices=[
        ("coupons", "Coupons"),
        ("promo_code", "Discount Code"),
    ])
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="loyalty_programs")
    currency = models.ForeignKey("app.Currency", on_delete=models.PROTECT, related_name="loyalty_programs")
    active = models.BooleanField(default=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)

    limit_usage = models.BooleanField(default=False)
    max_usage = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    # def prepare_odoo_data(self):
    #     return OdooSync.prepare_loyalty_program_data(self)


class PromoReward(SyncSoftDeleteMixin):
    reward_type = models.CharField(max_length=20, choices=[
        ("discount", "Discount"),
    ], default="discount")

    discount = models.FloatField(default=0.0)
    discount_applicability = models.CharField(max_length=20, choices=[
        ("order", "Order"),
        ('cheapest', 'Cheapest'),
        ("specific", "Specific"),
    ], default="order")

    program = models.ForeignKey(LoyaltyProgram, on_delete=models.SET_NULL, null=True, blank=True, related_name="promocode_rewards")
    number_of_people_case = models.PositiveIntegerField(default=1)
    is_new_coming_reward = models.BooleanField(default=False)
    discount_line_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="promocode_rewards")
    discount_product_ids = models.ManyToManyField(Product, blank=True, related_name="promocode_rewards_many")
    discount_product_category_id = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="promocode_rewards")
    discount_max_amount = models.FloatField(default=0.0)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.reward_type} - {self.discount}"

    # def prepare_odoo_data(self):
    #     return OdooSync.prepare_promo_reward_data(self)


class PromoCode(SyncSoftDeleteMixin):
    code = models.CharField(max_length=100, unique=True)

    expiration_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    points = models.PositiveIntegerField(default=0)

    program = models.ForeignKey(LoyaltyProgram, on_delete=models.SET_NULL, null=True, blank=True, related_name="promocodes")

    partner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.code

    # def prepare_odoo_data(self):
    #     return OdooSync.prepare_promo_code_data(self)
    

class LoyaltyRule(SyncSoftDeleteMixin):

    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rules"
    )

    min_quantity = models.PositiveIntegerField(default=1)
    min_amount = models.FloatField(default=0.0)

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyalty_rules"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyalty_rules"
    )

    cumulative = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.program.name if self.program else 'No Program'})"

    # def prepare_odoo_data(self):
    #     return OdooSync.prepare_loyalty_rule_data(self)