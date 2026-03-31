import uuid

from django.core.exceptions import ValidationError
from django.db import models
import os,json
import logging
from app.utils.control_signal import disable_signals
from django.utils import timezone
logger = logging.getLogger(__name__)
from django.core.serializers.json import DjangoJSONEncoder
from contextlib import contextmanager
from uuid import uuid4
import time
import traceback

class SyncSoftDeleteMixin(models.Model):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[('created', 'Created'), ('updated', 'Updated'), ('deleted', 'Deleted'), ('synced', 'Synced')],
        default='created'
    )
    send_odoo = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def clean(self):
        """Odoo ID unikal ekanligini tekshirish"""
        if self.odoo_id:
            if (
                self.__class__.objects.filter(odoo_id=self.odoo_id)
                .exclude(pk=self.pk)
                .exists()
            ):
                raise ValidationError({"odoo_id": "This odoo_id already exists."})

    def _get_model_mapping(self):
        """Model nomlarini Odoo modellari bilan bog'lash"""
        return {
            "User": ("res.partner", "user.models.User"),
            "Product": ("product.product", "app.models.product.Product"),
            "ProductTemplate": (
                "product.template",
                "app.models.product.ProductTemplate",
            ),
            "Variant": ("product.attribute", "app.models.product.Variant"),
            "Option": ("product.template.attribute.value", "app.models.product.Option"),
            "Branch": ("res.company", "app.models.company_info.Branch"),
            "Location": ("stock.location", "app.models.product.Location"),
            "WareHouse": ("stock.warehouse", "app.models.product.WareHouse"),
            "Category": ("product.category", "app.models.product.Category"),
            "ProductVariants": (
                "product.template.attribute.line",
                "app.models.product.ProductVariants",
            ),
            "ProductOption": (
                "product.template.attribute.value",
                "app.models.product.ProductOption",
            ),
            "StockQuant": ("stock.quant", "app.models.product.StockQuant"),
            "Pricelist": ("product.pricelist", "app.models.product.Pricelist"),
            "Discount": ("product.pricelist.item", "app.models.product.Discount"),
            "Region": ("uz.regions", "app.models.order.Region"),
            "District": ("uz.districts", "app.models.order.District"),
            "DeliveryPrice": (
                "custom.delivery.price",
                "app.models.order.DeliveryPrice",
            ),
            "OilBrand": ("oil.brand", "app.models.product.OilBrand"),
            "Booking": ("calendar.event", "app.models.booking.Booking"),
            "Firm": ("car.brand", "app.models.garage.Firm"),
            "CarModel": ("cashback.cars", "app.models.garage.CarModel"),
            "SomeColor": ("some.color", "app.models.garage.SomeColor"),
            "CarColor": ("car.color", "app.models.garage.CarColor"),
            "Car": ("res.partner", "app.models.garage.Car"),
            "Order": ("sale.order", "app.models.order.Order"),
            "Address": ("res.partner", "user.models.Address"),
            "OrderItem": ("sale.order.line", "app.models.order.OrderItem"),
            "BalanceStatus": ("balance.status", "app.models.card.BalanceStatus"),
            "Brand": ("product.brand", "app.models.product.Brand"),
            "ProductRating": ("product.rating", "app.models.product.ProductRating"),
            "OilChangeRating": (
                "oil.change.rating",
                "app.models.garage.OilChangeRating",
            ),
            "RatingType": ("custom.rating.type", "app.models.order.RatingType"),
            "OrderRating": ("order.rating", "app.models.order.OrderRating"),
            'ProductTemplateImage':('product.image','app.models.product.ProductTemplateImage'),
            'OilChangedHistory':('oil.changed.history','app.models.garage.OilChangedHistory'),
            'RequestForm':('request.form','app.models.company_info.RequestForm'),
            'Appointment':('appointment.type','app.models.booking.Appointment'),
            'AppointmentWorkingDay':('appointment.slot','app.models.booking.AppointmentWorkingDay'),
        }

    def define_model_name(self):
        """Model nomi va klass yo'lini aniqlash"""
        model_name = self.__class__.__name__
        return self._get_model_mapping().get(model_name, ("", ""))

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = not self.pk or not self.__class__.objects.filter(pk=self.pk).exists()
        odoo_send = self.send_odoo

        # ✅ Dirty fieldsni oldindan aniqlab olamiz
        dirty_fields = self.get_dirty_fields() if not is_new else {}

        # odoo'dan operatsiya qilish bo'lsa
        skip_from_odoo = kwargs.pop("skip_from_odoo", False)

        has_odoo_id = bool(self.odoo_id)

        if self.odoo_id is None:
            self.odoo_id = str(uuid.uuid4())
        self.send_odoo = True
        super().save(*args, **kwargs)

        if odoo_send and not skip_from_odoo:
            if is_new or (not is_new and not has_odoo_id):
                success = self._run_odoo_operation("create")
                if success:
                    self.sync_status = "synced"
                    with disable_signals():
                        super().save(update_fields=["sync_status"])
            elif self.odoo_id and (
                dirty_fields
                or self.__class__.__name__ in ["User", "ProductVariants"]
            ):
                success = self._run_odoo_operation("update")
                if success:
                    self.sync_status = "synced"
                    with disable_signals():
                        super().save(update_fields=["sync_status"])

    def delete(self, using=None, keep_parents=False,skip_odoo=False):
        """O'chirish va Odoo bilan sinxronizatsiya"""
        model_name, _ = self.define_model_name()
        if not model_name:
            return super().delete(using, keep_parents)
        if skip_odoo:
            return super().delete(using, keep_parents)

        if model_name not in ["res.company", "stock.warehouse", "stock.location"]:
            self._run_odoo_operation("delete", e_id=self.odoo_id)
            return super().delete(using, keep_parents)
        return

    def _run_odoo_operation(self, operation_type, **kwargs):
        """Odoo operatsiyasini bajarish"""
        from app.tasks import run_odoo_operation

        model_name, class_path = self.define_model_name()
        if not model_name or not class_path:
            logger.warning(f"Model mapping not found for {self.__class__.__name__}")
            return False

        return run_odoo_operation(
            operation_type=operation_type,
            model_name=model_name,
            instance_id=self.pk,
            instance_odoo_id=self.odoo_id,
            model_class_path=class_path,
            odoo_id_field="odoo_id",
            **kwargs,
        )

    def get_dirty_fields(self):
        """O'zgartirilgan maydonlarni aniqlash"""
        if not self.pk:
            return {}

        current_state = self.__class__.objects.get(pk=self.pk)
        return {
            field.name: getattr(current_state, field.name)
            for field in self._meta.fields
            if getattr(current_state, field.name) != getattr(self, field.name)
        }


class OdooConnectorLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("retrying", "Retrying"),
    ]

    OPERATION_TYPES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("read", "Read"),
    ]

    # Asosiy maydonlar
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    operation_type = models.CharField(max_length=10, choices=OPERATION_TYPES)
    model_name = models.CharField(max_length=255)
    local_model = models.CharField(max_length=255)
    instance_id = models.IntegerField(null=True, blank=True)
    odoo_id = models.CharField(max_length=255, null=True, blank=True)

    # Holat va natijalar
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    last_retry = models.DateTimeField(null=True, blank=True)

    # So'rov va javob detallari
    request_data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    response_data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    stack_trace = models.TextField(null=True, blank=True)

    # Performance metrikalari
    duration = models.FloatField(
        null=True, blank=True, help_text="Operation duration in seconds"
    )
    request_size = models.IntegerField(
        null=True, blank=True, help_text="Request size in bytes"
    )
    response_size = models.IntegerField(
        null=True, blank=True, help_text="Response size in bytes"
    )

    # Kontekst maydonlari
    correlation_id = models.UUIDField(null=True, blank=True, unique=True)
    initiated_by = models.CharField(max_length=255, null=True, blank=True)
    batch_id = models.UUIDField(null=True, blank=True)

    class Meta:
        verbose_name = "Odoo Connector Log"
        verbose_name_plural = "Odoo Connector Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "operation_type"]),
            models.Index(fields=["status", "timestamp"]),
            models.Index(fields=["odoo_id"]),
            models.Index(fields=["correlation_id"]),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} on {self.model_name} (Local ID: {self.instance_id}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Request va response hajmini hisoblash
        if self.request_data:
            self.request_size = len(json.dumps(self.request_data))
        if self.response_data:
            self.response_size = len(json.dumps(self.response_data))

        super().save(*args, **kwargs)

    @classmethod
    def start_log(
        cls,
        operation_type,
        model_name,
        local_model,
        instance_id,
        odoo_id=None,
        request_data=None,
    ):
        """Yangi log yozuvini boshlash"""
        return cls.objects.create(
            operation_type=operation_type,
            model_name=model_name,
            local_model=local_model,
            instance_id=instance_id,
            odoo_id=odoo_id,
            request_data=request_data,
            status="pending",
        )

    def mark_success(self, response_data, duration=None):
        """Logni muvaffaqiyatli yakunlangan deb belgilash"""
        self.status = "success"
        self.response_data = response_data
        self.duration = duration
        self.save()

    def mark_failed(
        self, error_message, stack_trace=None, response_data=None, duration=None
    ):
        """Logni muvaffaqiyatsiz yakunlangan deb belgilash"""
        self.status = "failed"
        self.error_message = str(error_message)[
            :2000
        ]  # Ensure we don't exceed text field limits
        self.stack_trace = stack_trace
        self.response_data = response_data
        self.duration = duration
        self.save()

    def mark_retrying(self, error_message, retry_count):
        """Logni qayta urinish jarayonida deb belgilash"""
        self.status = "retrying"
        self.error_message = str(error_message)[:2000]
        self.retry_count = retry_count
        self.last_retry = timezone.now()
        self.save()

    def get_operation_details(self):
        """Operatsiya detallarini dict ko'rinishida qaytarish"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.get_operation_type_display(),
            "model": self.model_name,
            "local_model": self.local_model,
            "instance_id": self.instance_id,
            "odoo_id": self.odoo_id,
            "status": self.get_status_display(),
            "duration": self.duration,
            "retry_count": self.retry_count,
            "error": self.error_message,
        }


class OdooConnectorLogger:
    def __init__(
        self,
        operation_type,
        model_name,
        local_model,
        instance_id,
        odoo_id=None,
        request_data=None,
    ):
        self.operation_type = operation_type
        self.model_name = model_name
        self.local_model = local_model
        self.instance_id = instance_id
        self.odoo_id = odoo_id
        self.request_data = request_data
        self.correlation_id = uuid4()
        self.log_entry = None
        self.start_time = None

    @contextmanager
    def log_operation(self):
        """Kontekst menejeri orqali operatsiyani log qilish"""
        self.start_time = time.time()
        self.log_entry = OdooConnectorLog.start_log(
            operation_type=self.operation_type,
            model_name=self.model_name,
            local_model=self.local_model,
            instance_id=self.instance_id,
            odoo_id=self.odoo_id,
            request_data=self.request_data,
        )
        self.log_entry.correlation_id = self.correlation_id
        self.log_entry.save()

        try:
            yield self.log_entry
        except Exception as e:
            duration = time.time() - self.start_time
            self.log_entry.mark_failed(
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                duration=duration,
            )
            raise
        else:
            duration = time.time() - self.start_time
            self.log_entry.mark_success(
                response_data=getattr(self, "response_data", None), duration=duration
            )

    def update_response(self, response_data):
        """Javob ma'lumotlarini yangilash"""
        self.response_data = response_data
        if self.log_entry:
            self.log_entry.response_data = response_data
            self.log_entry.save()

    def log_retry(self, error_message, retry_count):
        """Qayta urinishni log qilish"""
        if self.log_entry:
            self.log_entry.mark_retrying(error_message, retry_count)
