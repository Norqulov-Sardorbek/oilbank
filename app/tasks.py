import os
from .utils.odoo_sync_utils import execute_odoo_operation
import logging
from celery import shared_task
from django.conf import settings
from django.utils.timezone import now, timedelta

logger = logging.getLogger("odoo_sync")


def run_odoo_operation(
    operation_type, model_name, instance_id, model_class_path, **kwargs
):
    """Celery yoki sync ishlashini environment ga qarab boshqarish"""
    if os.getenv("USE_CELERY", "1") == "1":
        # Celery orqali async ishlatish
        task_func = {
            "create": create_in_odoo,
            "update": send_to_odoo_task,
            "delete": send_to_odoo_task_to_delete,
        }.get(operation_type)

        if task_func:
            return task_func.delay(model_name, instance_id, model_class_path, **kwargs)
        return False
    else:
        # To'g'ridan-to'g'ri sync ishlatish
        return execute_odoo_operation(
            operation_type, model_name, instance_id, model_class_path, **kwargs
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_to_odoo_task(self, model_name, instance_id, model_class_path, **kwargs):
    try:
        logger.info(f"[TASK START] UPDATE {model_name} #{instance_id}")
        result = execute_odoo_operation(
            "update", model_name, instance_id, model_class_path, **kwargs
        )
        logger.info(f"[TASK SUCCESS] UPDATE {model_name} #{instance_id} → {result}")
        return result
    except Exception as exc:
        logger.error(
            f"[TASK ERROR] UPDATE {model_name} #{instance_id} → {str(exc)}",
            exc_info=True,
        )
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_in_odoo(self, model_name, instance_id, model_class_path, **kwargs):
    ODOO_SYNC_DELAY_SECONDS = getattr(settings, "ODOO_SYNC_DELAY_SECONDS", 5)
    try:

        from time import sleep
        if model_name == "sale.order.line":
            print(f"\n\n\n\n{model_name}\n\n\n\n")
            ODOO_SYNC_DELAY_SECONDS += 7
        sleep(ODOO_SYNC_DELAY_SECONDS)

        logger.info(f"[TASK START] CREATE {model_name} #{instance_id}")
        result = execute_odoo_operation(
            "create", model_name, instance_id, model_class_path, **kwargs
        )
        logger.info(f"[TASK SUCCESS] CREATE {model_name} #{instance_id} → {result}")
        return result
    except Exception as exc:
        logger.error(
            f"[TASK ERROR] CREATE {model_name} #{instance_id} → {str(exc)}",
            exc_info=True,
        )
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_to_odoo_task_to_delete(
    self, model_name, instance_id, model_class_path, **kwargs
):
    try:
        logger.info(f"[TASK START] DELETE {model_name} #{instance_id}")
        result = execute_odoo_operation(
            "delete", model_name, instance_id, model_class_path, **kwargs
        )
        logger.info(f"[TASK SUCCESS] DELETE {model_name} #{instance_id} → {result}")
        return result
    except Exception as exc:
        logger.error(
            f"[TASK ERROR] DELETE {model_name} #{instance_id} → {str(exc)}",
            exc_info=True,
        )
        self.retry(exc=exc)


@shared_task(name="app.tasks.run_all_notifications")
def run_all_notifications():
    from app.utils.notification_utils import create_oil_change_notifications, create_order_notifications
    create_oil_change_notifications()
    create_order_notifications()


@shared_task
def send_booking_reminder(booking_id: int, when: str):
    from pytz import timezone
    from app.models import Booking
    from app.utils.notification_utils import create_notification

    booking = Booking.objects.select_related('user', 'car', 'branch').filter(id=booking_id).first()
    if not booking or not booking.user or not booking.car:
        return

    lang = booking.user.get_language() or "uz"
    car_name = f"{booking.car.firm.name} {booking.car.model.name}" if booking.car else "Unknown"
    car_plate = booking.car.number if booking.car else "Unknown"
    filial = booking.branch.name if booking.branch else "Filial"

    tz = timezone("Asia/Tashkent")
    localized_start = booking.start_time.astimezone(tz)
    date = localized_start.strftime("%Y-%m-%d")
    time = localized_start.strftime("%H:%M")

    context = {
        "car_name": car_name,
        "car_plate": car_plate,
        "filial": filial,
        "date": date,
        "time": time
    }

    title = {}
    message = {}
    sms_message = None
    should_send_sms_flag = True

    if when == "1_day":
        title = {
            "uz": "🟠 1 kun oldin eslatma",
            "ru": "🟠 Напоминание за 1 день",
            "en": "🟠 1 day reminder"
        }
        message = {
            "uz": f"🕑 Eslatma: ertaga {car_name} ({car_plate}) uchun navbat. 📅 {date}, ⏰ {time} 📍 {filial}",
            "ru": f"🕑 Напоминание: завтра запись для {car_name} ({car_plate}). 📅 {date}, ⏰ {time} 📍 {filial}",
            "en": f"🕑 Reminder: tomorrow booking for {car_name} ({car_plate}). 📅 {date}, ⏰ {time} 📍 {filial}"
        }
        sms_message = {
            "uz": f"Ertaga filial: {filial}dagi navbatingizga: {date}, {time}. {car_name} ({car_plate}) – Carland.uz",
            "ru": f"Завтра ваша очередь в филиале {filial}: {date}, {time}. {car_name} ({car_plate}) — Carland.uz",
            "en": f"Tomorrow is your turn at branch {filial}: {date}, {time}. {car_name} ({car_plate}) — Carland.uz"
        }.get(lang)

    elif when == "2_hours":
        title = {
            "uz": "🕓 2 soat oldin eslatma",
            "ru": "🕓 Напоминание за 2 часа",
            "en": "🕓 2 hours reminder"
        }
        message = {
            "uz": f"⏰ 2 soat qoldi: {car_name} ({car_plate}) navbatiga. ⏰ {time} 📍 {filial}",
            "ru": f"⏰ Осталось 2 часа до записи: {car_name} ({car_plate}). ⏰ {time} 📍 {filial}",
            "en": f"⏰ 2 hours left until booking: {car_name} ({car_plate}). ⏰ {time} 📍 {filial}"
        }
        sms_message = {
            "uz": f"Filial: {filial}da 2 soatdan so‘ng navbat: {time}. {car_name} ({car_plate}) – Carland.uz",
            "ru": f"Филиал: {filial}, очередь через 2 часа: {time}. {car_name} ({car_plate}) — Carland.uz",
            "en": f"Branch: {filial}, your turn in 2 hours: {time}. {car_name} ({car_plate}) — Carland.uz"
        }.get(lang)

    create_notification(
        content_object=booking,
        notification_type=f"booking_reminder_{when}",
        context=context,
        title=title,
        message=message,
        user=booking.user,
        should_send_sms=should_send_sms_flag,
        sms_message=sms_message
    )





