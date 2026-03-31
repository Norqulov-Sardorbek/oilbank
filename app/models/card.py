import os

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
import os
# locals
from .garage import Car
from .order import Order,Product
from .booking import Booking
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

# utils
from uuid import uuid4
import pytz
from django.utils.translation import gettext_lazy as _
from .log_connection import SyncSoftDeleteMixin
from ..utils.utils import OdooSync

User = get_user_model()


# Create a path to save the card images
def card_image_file_path(instance, filename) -> str:
    """
    This function generates a name for saving the
    card image and creates a path to the appropriate folder.
    """
    extention = str(filename).split(".")[-1]
    new_filename = f"{filename}-{uuid4()}.{extention}"
    return os.path.join("card-images/", new_filename)


class CardImages(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    image = models.FileField(upload_to=card_image_file_path)

    def __str__(self):
        return self.image.name


class Card(SyncSoftDeleteMixin):

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    # user using the card in the system
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="cards"
    )

    card_token = models.CharField(max_length=255)

    owner = models.CharField(max_length=255)  # the legal owner of the card
    card_name = models.CharField(max_length=128)
    card_number = models.CharField(max_length=16)
    phone_number = models.CharField(max_length=20)
    processing = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)

    background_image = models.ForeignKey(
        CardImages, on_delete=models.CASCADE, related_name="background_images"
    )
    is_main = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensuring that each user has one main card
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_main=True),
                name="unique_is_main_per_user",
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_main:
            Card.objects.filter(user=self.user, is_main=True).update(is_main=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.card_name} - {self.card_number}"


class LoyaltyCard(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    car = models.OneToOneField(
        Car,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loyalty_card",
    )

    card_name = models.CharField(max_length=128)
    card_number = models.CharField(max_length=16)
    expiration_date = models.CharField(max_length=8)
    processing = models.CharField(max_length=100)

    balance = models.DecimalField(decimal_places=2, max_digits=16, default=0.0)
    is_active = models.BooleanField(default=True)

    background_image = models.ForeignKey(
        CardImages, on_delete=models.CASCADE, related_name="loyalty_background_images"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_name} - {self.card_number}"


class BalanceStatus(SyncSoftDeleteMixin):
    class Status(models.TextChoices):
        DAYS = "day", _("Days")
        WEEKS = "week", _("Weeks")
        MONTHS = "month", _("Months")
        YEARS = "year", _("Years")

    name = models.CharField(max_length=255, unique=True)
    percentage = models.DecimalField(decimal_places=2, max_digits=16)
    minimum_amount = models.DecimalField(decimal_places=2, max_digits=16)
    next_minimum_amount = models.DecimalField(decimal_places=2, max_digits=16, null=True, blank=True)
    num = models.IntegerField(null=True, blank=True)
    time_line = models.CharField(
        max_length=255, choices=Status.choices, null=True, blank=True
    )
    description_uz = models.TextField(null=True, blank=True)
    description_ru = models.TextField(null=True, blank=True)
    description_en = models.TextField(null=True, blank=True)
    icon = models.ImageField(upload_to="balance_status/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def prepare_odoo_data(self):
        return OdooSync.prepare_balance_status_data(self)


class Balance(SyncSoftDeleteMixin):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="balances"
    )
    unique_id = models.CharField(max_length=255, null=True, blank=True)
    balance = models.DecimalField(decimal_places=2, max_digits=16)
    total_sales = models.DecimalField(decimal_places=2, max_digits=16)
    balance_status = models.ForeignKey(
        BalanceStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="balances",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.balance}"


class Cashback(SyncSoftDeleteMixin):
    class State(models.TextChoices):
        given = "given", _("Given")
        reversed = "reversed", _("Reversed")
        used = "used", _("Used")

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cashbacks",
    )
    balance = models.ForeignKey(
        Balance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cashbacks",
    )
    amount = models.DecimalField(
        decimal_places=2, max_digits=16, help_text="The amount of order"
    )
    state = models.CharField(
        max_length=255, choices=State.choices, null=True, blank=True
    )
    percentage = models.DecimalField(decimal_places=2, max_digits=16)
    cashback = models.DecimalField(decimal_places=2, max_digits=16)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order} - {self.amount}"


class Invoice(SyncSoftDeleteMixin):
    class Status(models.TextChoices):
        CREATED = "CRD", _("Created")
        NO_PRICE = "NP", _("No Price")
        WAITING = "WNG", _("Waiting")
        PAID = "PD", _("Paid")
        CANCELED = "CLD", _("Canceled")
        EXPIRED = "EXP", _("Expired")

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    transaction_number = models.IntegerField()
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(
        decimal_places=2, max_digits=16, default=0.0, null=True, blank=True
    )
    amount_payed = models.DecimalField(
        decimal_places=2, max_digits=16, default=0.0, null=True, blank=True
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    created_time = models.DateTimeField(auto_now_add=True)
    exp_time = models.DateTimeField()
    payment_date = models.DateField(null=True, blank=True)
    payment_time = models.TimeField(null=True, blank=True)

    status = models.CharField(
        max_length=3, choices=Status.choices, default=Status.CREATED
    )
    fiscal_url=models.CharField(max_length=255, null=True, blank=True)
    f_num = models.CharField(max_length=255, null=True, blank=True)
    fm_num = models.CharField(max_length=255, null=True, blank=True)
    balance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0) # how much cashback taken from user

    @property
    def amount_left(self):
        return self.amount - self.amount_payed

    def save(self, *args, **kwargs):
        if not self.pk:
            last_invoice = Invoice.objects.order_by("-transaction_number").first()
            self.transaction_number = (
                last_invoice.transaction_number + 1 if last_invoice else 1
            )

        # # auto add exp time
        # if not self.exp_time:
        #     self.exp_time = timezone.now() + timedelta(days=10)

        if self.payment_date:
            uzbekistan_timezone = pytz.timezone("Asia/Tashkent")
            self.payment_time = timezone.now().astimezone(uzbekistan_timezone).time()

        if self.amount == self.amount_payed:
            self.status = self.Status.PAID

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.pk} - {self.status}"


class CheckForUser(models.Model):
    transaction_number = models.IntegerField()

    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.CharField(null=True,blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_check")
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_check"
    )
    products = models.ManyToManyField(Product,related_name='products_for_check')

    fiscal_url=models.CharField(max_length=255, null=True, blank=True)
    f_num = models.CharField(max_length=255, null=True, blank=True)
    fm_num = models.CharField(max_length=255, null=True, blank=True)

    balance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0) # how much cashback taken from user
    given_cashback = models.DecimalField(max_digits=14, decimal_places=2, default=0.0) 
    amount = models.DecimalField(
        decimal_places=2, max_digits=16, default=0.0, null=True, blank=True
    )

def get_or_create_check_for_order(order):
    # Only process if payment status is COMPLETED
    if order.payment_status != "COMPLETED":
        return None, False
    
    # Check if a check already exists for this order
    existing_check = CheckForUser.objects.filter(order=order).first()
    if existing_check:
        return existing_check, False
    
    # Create new check
    with transaction.atomic():
        # Get the next transaction number
        last_check = CheckForUser.objects.order_by('-transaction_number').first()
        next_transaction_number = (last_check.transaction_number + 1) if last_check else 1
        total = order.price - order.balance_amount
        percentage = Decimal(str(order.balance_percentage)) if order.balance_percentage is not None else Decimal("0.00")
        given_cashback = total * (percentage / Decimal("100"))

        check = CheckForUser.objects.create(
            transaction_number=next_transaction_number,
            transaction_id=order.raxmat_payment_id,
            payment_type=order.payment_method,
            user=order.user,
            order=order,
            fiscal_url=order.fiscal_url,
            f_num=order.f_num,
            fm_num=order.fm_num,
            balance_amount=order.balance_amount,
            given_cashback=Decimal(given_cashback),  
            amount=order.price
        )
        
        # Add products from order items
        for item in order.items.all():
            if item.product:
                check.products.add(item.product)
        return check, True


class BalanceUsageLimit(models.Model):
    """
    Model to define the usage limits for balance.
    """

    min_amount = models.DecimalField(decimal_places=2, max_digits=16, default=0.0)
    max_amount = models.DecimalField(decimal_places=2, max_digits=16, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.min_amount} - {self.max_amount}"
