from django.db.models.signals import m2m_changed
from pytz import timezone
from app.models import ProductTemplate, Product
from django.db import transaction

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from app.models import Booking
from app.utils.booking_service import schedule_booking_reminders
from app.utils.notification_utils import create_notification
from app.utils.control_signal import signals_enabled


@receiver(m2m_changed, sender=Product.attributes.through)
def update_price_on_attributes_change(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.price = instance.calculate_price()
        instance.save(update_fields=["price"])


@receiver(post_save, sender=ProductTemplate)
def update_product_prices_after_template_save(sender, instance, created, **kwargs):
    def update_related_products():
        for product in instance.products.all():
            product.price = product.calculate_price()
            product.send_odoo = False
            product.save(update_fields=["price", "send_odoo"])

    transaction.on_commit(update_related_products)



booking_previous_state = {}
@receiver(pre_save, sender=Booking)
def booking_pre_save(sender, instance, **kwargs):
    if instance.id:
        try:
            previous = Booking.objects.get(id=instance.id)
            booking_previous_state[instance.id] = {
                'start_time': previous.start_time
            }
        except Booking.DoesNotExist:
            booking_previous_state[instance.id] = {}

@receiver(post_save, sender=Booking)
def booking_post_save(sender, instance, created, **kwargs):
    if not signals_enabled():
        return

    if instance.status == "CONFIRMED":
        schedule_booking_reminders(instance)

    if not created:  # Status change or update check
        lang = instance.user.get_language() if instance.user else "uz"
        uz_tz = timezone("Asia/Tashkent")
        localized = instance.start_time.astimezone(uz_tz)
        date = localized.strftime("%Y-%m-%d")
        time = localized.strftime("%H:%M")
        car_name = f"{instance.car.firm.name} {instance.car.model.name}" if instance.car else "Unknown"
        car_plate = instance.car.number if instance.car else "Unknown"
        filial = instance.branch.name if instance.branch else "Filial"

        context = {
            "car_name": car_name,
            "car_plate": car_plate,
            "filial": filial,
            "date": date,
            "time": time
        }

        if instance.status == "CONFIRMED":
            create_notification(
                content_object=instance,
                notification_type="booking_confirmed",
                context=context,
                title={
                    'uz': "✅ Navbat tasdiqlandi",
                    'ru': "✅ Запись подтверждена",
                    'en': "✅ Booking confirmed"
                },
                message={
                    'uz': f"✅ {car_name} ({car_plate}) uchun moy almashtirish navbati tasdiqlandi! 📅 {date}, ⏰ {time} 📍 {filial}",
                    'ru': f"✅ Запись на замену масла для {car_name} ({car_plate}) подтверждена! 📅 {date}, ⏰ {time} 📍 {filial}",
                    'en': f"✅ Oil change booking for {car_name} ({car_plate}) confirmed! 📅 {date}, ⏰ {time} 📍 {filial}"
                },
                user=instance.user,
                should_send_sms=True,
                sms_message={
                    'uz': f"Filial: {filial}dagi navbatingiz tasdiqlandi: {date}, {time}. {car_name} ({car_plate}) – Carland.uz",
                    'ru': f"Филиал: {filial} — ваша запись подтверждена: {date}, {time}. {car_name} ({car_plate}) — Carland.uz",
                    'en': f"Branch: {filial} — your appointment is confirmed: {date}, {time}. {car_name} ({car_plate}) — Carland.uz"
                }.get(lang)
            )

        elif instance.status == "CANCELLED":
            create_notification(
                content_object=instance,
                notification_type="booking_cancelled",
                context=context,
                title={
                    'uz': "❌ Navbat bekor qilindi",
                    'ru': "❌ Запись отменена",
                    'en': "❌ Booking cancelled"
                },
                message={
                    'uz': f"❌ Moy almashtirish navbati bekor qilindi. {car_name} ({car_plate}) – {date}, {time}",
                    'ru': f"❌ Запись на замену масла отменена. {car_name} ({car_plate}) – {date}, {time}",
                    'en': f"❌ Oil change booking cancelled. {car_name} ({car_plate}) – {date}, {time}"
                },
                user=instance.user,
                should_send_sms=True,
                sms_message={
                    'uz': f"Filial: {filial}dagi navbat bekor qilindi: {date}, {time}. {car_name} ({car_plate}) – Carland.uz",
                    'ru': f"Филиал: {filial}, ваша очередь отменена: {date}, {time}. {car_name} ({car_plate}) — Carland.uz",
                    'en': f"Branch: {filial}, your appointment has been cancelled: {date}, {time}. {car_name} ({car_plate}) — Carland.uz"
                }.get(lang)
            )

        elif instance.status == "COMPLETED":
            create_notification(
                content_object=instance,
                notification_type="booking_completed",
                context=context,
                title={
                    'uz': "✅ Xizmat bajarildi",
                    'ru': "✅ Услуга выполнена",
                    'en': "✅ Service completed"
                },
                message={
                    'uz': f"✅ {car_name} ({car_plate}) uchun moy almashtirish bajarildi. Xizmat tarixi yangilandi.",
                    'ru': f"✅ Замена масла для {car_name} ({car_plate}) выполнена. История обслуживания обновлена.",
                    'en': f"✅ Oil change for {car_name} ({car_plate}) completed. Service history updated."
                },
                user=instance.user,
                should_send_sms=False,
                sms_message=None
            )

        previous_start_time = booking_previous_state[instance.id].get('start_time')
        if previous_start_time != instance.start_time:
            create_notification(
                content_object=instance,
                notification_type="booking_time_updated",
                context=context,
                title={
                    'uz': "ℹ️ Navbat vaqti yangilandi",
                    'ru': "ℹ️ Время записи обновлено",
                    'en': "ℹ️ Booking time updated"
                },
                message={
                    'uz': f"ℹ️ Navbat vaqti yangilandi: {car_name} ({car_plate}) 📅 {date}, ⏰ {time} 📍 {filial}",
                    'ru': f"ℹ️ Время записи обновлено: {car_name} ({car_plate}) 📅 {date}, ⏰ {time} 📍 {filial}",
                    'en': f"ℹ️ Booking time updated: {car_name} ({car_plate}) 📅 {date}, ⏰ {time} 📍 {filial}"
                },
                user=instance.user,
                should_send_sms=True,
                sms_message={
                    'uz': f"Filial: {filial}dagi navbatingiz yangilandi: {date}, {time}. {car_name} ({car_plate}) – Carland.uz",
                    'ru': f"Филиал: {filial}, ваша очередь обновлена: {date}, {time}. {car_name} ({car_plate}) — Carland.uz",
                    'en': f"Branch: {filial}, your appointment has been updated: {date}, {time}. {car_name} ({car_plate}) — Carland.uz"
                }.get(lang)
            )
