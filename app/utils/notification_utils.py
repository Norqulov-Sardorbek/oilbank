import json
from datetime import datetime
from user.models import User, MessageLog
from celery import shared_task
from user.tasks import send_sms

from app.models import Order
from app.models.garage import OilChangedHistory
from app.models.notification import Notification
from app.serializers.notification import NotificationSerializer
from app.serializers.garage import OilChangedHistoryNotificationSerializer
from django.contrib.contenttypes.models import ContentType
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification as FCMNotification
from firebase_admin.messaging import UnregisteredError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def create_notification(content_object, notification_type, context, title, message, user=None, should_send_sms=False,
                        sms_message=None):
    try:
        # declare variables
        user_language = user.get_language() if user else None
        content_type = ContentType.objects.get_for_model(content_object) if content_object else None
        object_id = content_object.id if content_object else None

        if should_send_sms and user and user.phone:
            sms_text = sms_message or message.get(user_language) or ""
            if not sms_text.strip():
                logger.warning(f"No SMS text provided for user {user.id}")
            else:
                # Check for SMS duplicate via MessageLog
                existing_sms = MessageLog.objects.filter(
                    content_type=content_type,
                    object_id=object_id,
                    message_type=notification_type,
                    context=context,
                    recipient=user.phone,
                ).exists()

                if not existing_sms:
                    send_sms.delay(
                        user.phone,
                        sms_text,
                        content_type.id if content_type else None,
                        object_id,
                        notification_type,
                        context,
                    )
                    logger.warning(f"SMS sent to user {user.id}, phone {user.phone}: {sms_text}")
                else:
                    logger.warning(f"SMS duplicate skipped: user {user.id}, phone {user.phone}")
        else:
            logger.warning(f"SMS not sent: user {user} or phone not available")

        # Check for duplicate notification
        if Notification.objects.filter(
                content_type=content_type,
                object_id=object_id,
                notification_type=notification_type,
                context=context
        ).exists():
            logger.warning(f"Duplicate notification skipped: {notification_type}, context: {context}")
            return None

        logger.warning(f"Creating notification: {notification_type} for object {object_id} of type {content_type}, user: {user}, phone: {user.phone if user else 'N/A'}")

        # Create notification
        notification = Notification.objects.create(
            content_type=content_type,
            object_id=object_id,
            notification_type=notification_type,
            context=context,
            title_en=title.get('en', ''),
            title_uz=title.get('uz', ''),
            title_ru=title.get('ru', ''),
            message_en=message.get('en', ''),
            message_uz=message.get('uz', ''),
            message_ru=message.get('ru', ''),
        )

        fcm_notification = FCMNotification(
            title=title.get(user_language, title.get('uz', 'Notification')),
            body=message.get(user_language, message.get('uz', 'New notification')),
        )
        notification_data = NotificationSerializer(notification).data

        if user:
            # User-specific notification
            notification.send_users.add(user)
            notification.save()
            logger.warning(f"json notification: {json.dumps(notification_data)}")

            # Get all active devices for the user
            devices = FCMDevice.objects.filter(user=user, active=True)
            if not devices.exists():
                logger.warning(f"No active FCM devices found for user {user.id}")
                return notification

            for device in devices:
                try:
                    # Send to individual device token
                    message = Message(
                        notification=fcm_notification,
                        token=device.registration_id,  # Use device token
                        data={
                            'notification': json.dumps(notification_data) if isinstance(notification_data, dict) else notification_data,
                            'type': 'user_specific',
                        }
                    )
                    response = device.send_message(message)  # Use device.send_message
                    logger.info(f"Sent user-specific notification to user {user.id}, device {device.id}: {response}")
                except UnregisteredError as e:
                    logger.error(f"Unregistered FCM token for user {user.id}, device {device.id}: {e}")
                    device.active = False
                    device.save()
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user.id}, device {device.id}: {e}")

        else:
            # Global notification
            message = Message(
                notification=fcm_notification,
                topic='global_notifications',
                data={
                    'notification': str(notification_data),
                    'type': 'global',
                }
            )
            try:
                response = FCMDevice.objects.send_message(message)
                logger.info(f"Sent global notification: {response}")
            except UnregisteredError as e:
                logger.error(f"Unregistered FCM token for global notification: {e}")
                FCMDevice.objects.filter(active=True).update(active=False)
            except Exception as e:
                logger.error(f"Failed to send global notification: {e}")

        return notification

    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None


def create_oil_change_notifications(context=None):
    """
    Check OilChangedHistory records and create notifications for upcoming expirations.
    """
    oil_changes = OilChangedHistory.objects.all()
    serializer = OilChangedHistoryNotificationSerializer(oil_changes, many=True)
    today = datetime.today().date()
    notification_days = getattr(settings, 'NOTIFICATION_DAYS', [0, 1, 2, 3, 5, 10])

    for oil_change, data in zip(oil_changes, serializer.data):
        try:
            next_oil_change_date = datetime.strptime(
                data['next_oil_change_date'], "%Y-%m-%d"
            ).date()
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid next_oil_change_date for OilChangedHistory {oil_change.id}: {e}")
            continue

        days_until_expiration = (next_oil_change_date - today).days

        if days_until_expiration in notification_days or days_until_expiration == 0:
            context_data = {
                'days_until_expiration': days_until_expiration,
                'predicted_date': next_oil_change_date.strftime("%Y-%m-%d"),
                'car_name': oil_change.car.model if oil_change.car else 'Unknown',
                'car_plate': oil_change.car.number if oil_change.car else 'Unknown'
            }
            title = {
                'uz': "Yog' almashtirish eslatmasi",
                'ru': "Напоминание о замене масла",
                'en': "Oil Change Reminder"
            }
            message = {}
            sms_message = None
            should_send_sms_flag = days_until_expiration in [10, 5, 3, 2, 1]

            if days_until_expiration == 10:
                message = {
                    'uz': f"🛢️ {context_data['car_name']} ({context_data['car_plate']}) uchun moy almashtirish muddati yaqinlashmoqda. 📅 {context_data['predicted_date']}",
                    'ru': f"🛢️ Для {context_data['car_name']} ({context_data['car_plate']}) приближается срок замены масла. 📅 {context_data['predicted_date']}",
                    'en': f"🛢️ {context_data['car_name']} ({context_data['car_plate']}), estimated time left for oil change: ~{context_data['days_until_expiration']} days. Nearest branches: Carland.uz"
                }
                sms_message = {
                    'uz': f"{context_data['car_name']} ({context_data['car_plate']}) moy almashtirish taxminiy qolgan vaqt: {context_data['days_until_expiration']} kun. Eng yaqin filiallar: Carland.uz",
                    'ru': f"{context_data['car_name']} ({context_data['car_plate']}), до замены масла примерно {context_data['days_until_expiration']} дн. Ближайшие филиалы: Carland.uz",
                    'en': f"{context_data['car_name']} ({context_data['car_plate']}), estimated time left for oil change: ~{context_data['days_until_expiration']} days. Nearest branches: Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            elif days_until_expiration == 5:
                message = {
                    'uz': f"Eslatma: {context_data['car_name']} ({context_data['car_plate']}) uchun xizmat muddati yaqinlashmoqda. 📅 {context_data['predicted_date']}",
                    'ru': f"Напоминание: для {context_data['car_name']} ({context_data['car_plate']}) приближается срок обслуживания. 📅 {context_data['predicted_date']}",
                    'en': f"Reminder: {context_data['car_name']} ({context_data['car_plate']}), service deadline is approaching. 📅 {context_data['predicted_date']}"
                }
                sms_message = {
                    'uz': f"{context_data['car_name']} ({context_data['car_plate']}) moy almashtirish taxminiy qolgan vaqt: {context_data['days_until_expiration']} kun. Eng yaqin filiallar: Carland.uz",
                    'ru': f"{context_data['car_name']} ({context_data['car_plate']}), до замены масла примерно {context_data['days_until_expiration']} дн. Ближайшие филиалы: Carland.uz",
                    'en': f"{context_data['car_name']} ({context_data['car_plate']}), estimated time left for oil change: ~{context_data['days_until_expiration']} days. Nearest branches: Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            elif days_until_expiration == 3:
                message = {
                    'uz': f"⏳ {context_data['car_name']} ({context_data['car_plate']}) uchun xizmat vaqti yaqin. 📅 {context_data['predicted_date']}",
                    'ru': f"⏳ Для {context_data['car_name']} ({context_data['car_plate']}) срок обслуживания близок. 📅 {context_data['predicted_date']}",
                    'en': f"⏳ Service time for {context_data['car_name']} ({context_data['car_plate']}) is near. 📅 {context_data['predicted_date']}"
                }
                sms_message = {
                    'uz': f"Xizmat yaqin: {context_data['car_name']} ({context_data['car_plate']}) – {context_data['predicted_date']}. Yoziling: Carland.uz",
                    'ru': f"Срок обслуживания близок: {context_data['car_name']} ({context_data['car_plate']}) – {context_data['predicted_date']}. Запишитесь: Carland.uz",
                    'en': f"Service is near: {context_data['car_name']} ({context_data['car_plate']}) – {context_data['predicted_date']}. Book now: Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            elif days_until_expiration == 2:
                message = {
                    'uz': f"🔧 {context_data['car_name']} ({context_data['car_plate']}) uchun moy almashtirish tavsiya etiladi. 📅 {context_data['predicted_date']}",
                    'ru': f"🔧 Рекомендуется замена масла для {context_data['car_name']} ({context_data['car_plate']}). 📅 {context_data['predicted_date']}",
                    'en': f"🔧 Oil change recommended for {context_data['car_name']} ({context_data['car_plate']}). 📅 {context_data['predicted_date']}"
                }
                sms_message = {
                    'uz': f"{context_data['car_name']} ({context_data['car_plate']}) moy almashtirish taxminiy qolgan vaqt: {context_data['days_until_expiration']} kun. Eng yaqin filiallar: Carland.uz",
                    'ru': f"{context_data['car_name']} ({context_data['car_plate']}), до замены масла примерно {context_data['days_until_expiration']} дн. Ближайшие филиалы: Carland.uz",
                    'en': f"{context_data['car_name']} ({context_data['car_plate']}), estimated time left for oil change: ~{context_data['days_until_expiration']} days. Nearest branches: Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            elif days_until_expiration == 1:
                message = {
                    'uz': f"📅 Ertaga: {context_data['car_name']} ({context_data['car_plate']}) uchun moy almashtirish xizmati tavsiya qilinadi. Carland kutmoqda.",
                    'ru': f"📅 Завтра: рекомендуется замена масла для {context_data['car_name']} ({context_data['car_plate']}). Carland ждёт вас.",
                    'en': f"📅 Tomorrow: oil change service recommended for {context_data['car_name']} ({context_data['car_plate']}). Carland is waiting."
                }
                sms_message = {
                    'uz': f"{context_data['car_name']} ({context_data['car_plate']}) moy almashtirish taxminiy qolgan vaqt: {context_data['days_until_expiration']} kun. Eng yaqin filiallar: Carland.uz",
                    'ru': f"{context_data['car_name']} ({context_data['car_plate']}), до замены масла примерно {context_data['days_until_expiration']} дн. Ближайшие филиалы: Carland.uz",
                    'en': f"{context_data['car_name']} ({context_data['car_plate']}), estimated time left for oil change: ~{context_data['days_until_expiration']} days. Nearest branches: Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            elif days_until_expiration == 0:
                message = {
                    'uz': f"✅ {context_data['car_name']} ({context_data['car_plate']}) uchun moy almashtirish qayd qilindi. Yangi hisob boshlandi.",
                    'ru': f"✅ Для {context_data['car_name']} ({context_data['car_plate']}) замена масла зарегистрирована. Новый отсчёт начат.",
                    'en': f"✅ Oil change recorded for {context_data['car_name']} ({context_data['car_plate']}). New countdown started."
                }
                sms_message = {
                    'uz': f"{context_data['filial'] if 'filial' in context_data else 'Filial'} filialida {context_data['car_name']} ({context_data['car_plate']}) uchun moy almashtirildi. Ishonchingiz uchun tashakkur, ilovamizda bizni baholashni unutmang – Carland.uz",
                    'ru': f"В филиале {context_data['filial'] if 'filial' in context_data else 'Filial'} масло заменено для {context_data['car_name']} ({context_data['car_plate']}). Спасибо за доверие! Не забудьте оценить нас в приложении — Carland.uz",
                    'en': f"Oil has been changed for {context_data['car_name']} ({context_data['car_plate']}) at {context_data['filial'] if 'filial' in context_data else 'Branch'} branch. Thank you for your trust! Please don’t forget to rate us in the app — Carland.uz"
                }.get(oil_change.car.user.get_language() if oil_change.car.user else 'uz')

            create_notification(
                content_object=oil_change,
                notification_type='oil_change_reminder',
                context=context_data,
                title=title,
                message=message,
                user=oil_change.car.user,
                should_send_sms=should_send_sms_flag,
                sms_message=sms_message
            )


def create_order_notifications(context=None):
    all_orders = Order.objects.all()
    notification_type_order_status_mapping = {
        'PENDING': 'order_pending',
        'PROCESSING': 'order_processing',
        'COLLECTING': 'order_collecting',
        'READY': 'order_ready',
        'COMPLETED': 'order_completed',
        'CANCELLED': 'order_canceled',
    }

    for order in all_orders:
        notification_type = notification_type_order_status_mapping.get(order.status)
        if not notification_type:
            continue

        lang = order.user.get_language() if order.user else "uz"
        order_id = f"{order.id}-{order.name if order.name else ''}"
        branch_name = order.branch.name if order and order.branch else ""
        location = ((f"{order.address_id.region.name if order.address_id else ''} "
                     f"{order.address_id.district.name if order.address_id else ''}") or
                    f"{order.branch.city if order.branch else 'City'} "
                    f"{order.branch.street if order.branch else 'Street'}")

        title = {}
        message = {}
        sms_message = None
        should_send_sms_flag = False

        if order.status == 'PENDING':
            title = {
                'uz': "Buyurtma rasmiylashtirildi",
                'ru': "Заказ оформлен",
                'en': "Order placed",
            }
            message = {
                'uz': f"✅ Buyurtmangiz qabul qilindi! 🧾 Buyurtma raqami: #{order_id} Tez orada tasdiqlanadi.",
                'ru': f"✅ Ваш заказ принят! 🧾 Номер заказа: #{order_id} Скоро будет подтверждён.",
                'en': f"✅ Your order has been received! 🧾 Order number: #{order_id} It will be confirmed shortly."
            }
            should_send_sms_flag = False  # No SMS for PENDING as per the sheet
            sms_message = None

        elif order.status == 'PROCESSING':
            title = {
                'uz': "Buyurtma tasdiqlandi",
                'ru': "Заказ подтверждён",
                'en': "Order confirmed",
            }
            message = {
                'uz': f"✅ Buyurtmangiz tasdiqlandi! 🧾 Buyurtma raqami: #{order_id}",
                'ru': f"✅ Ваш заказ подтверждён! 🧾 Номер заказа: #{order_id}",
                'en': f"✅ Your order is confirmed! 🧾 Order number: #{order_id}"
            }
            should_send_sms_flag = True
            sms_message = {
                'uz': f"Buyurtmangiz tasdiqlandi (#{order_id}) – Carland.uz",
                'ru': f"Ваш заказ подтверждён (#{order_id}) – Carland.uz",
                'en': f"Your order is confirmed (#{order_id}) – Carland.uz"
            }.get(lang)

        elif order.status == 'COLLECTING':
            title = {
                'uz': "Buyurtma yo‘lda",
                'ru': "Заказ в пути",
                'en': "Order on the way",
            }
            message = {
                'uz': f"🚗 Buyurtmangiz yo‘lda! Buyurtma raqami: #{order_id}",
                'ru': f"🚗 Ваш заказ в пути! Номер заказа: #{order_id}",
                'en': f"🚗 Your order is on the way! Order number: #{order_id}"
            }
            should_send_sms_flag = False  # No SMS for COLLECTING as per the sheet
            sms_message = None

        elif order.status == 'READY':
            title = {
                'uz': "Buyurtma tayyor",
                'ru': "Заказ готов",
                'en': "Order ready",
            }
            message = {
                'uz': f"✅ Buyurtma tayyor! 🧾 Buyurtma raqami: #{order_id} Filial: {branch_name}, Manzil: {location}",
                'ru': f"✅ Заказ готов! 🧾 Номер заказа: #{order_id} Филиал: {branch_name}, Адрес: {location}",
                'en': f"✅ Order ready! 🧾 Order number: #{order_id} Branch: {branch_name}, Address: {location}"
            }
            should_send_sms_flag = True
            sms_message = {
                'uz': f"Buyurtmangiz tayyor (#{order_id}). Filial: {branch_name}. – Carland.uz",
                'ru': f"Ваш заказ готов (#{order_id}). Филиал: {branch_name}. – Carland.uz",
                'en': f"Your order is ready (#{order_id}). Branch: {branch_name}. – Carland.uz"
            }.get(lang)

        elif order.status == 'COMPLETED':
            title = {
                'uz': "Buyurtma topshirildi",
                'ru': "Заказ доставлен",
                'en': "Order delivered",
            }
            message = {
                'uz': f"✅ Buyurtma yetkazildi! 🧾 Buyurtma raqami: #{order_id} Fikringiz biz uchun muhim – ilovada baholang!",
                'ru': f"✅ Заказ доставлен! 🧾 Номер заказа: #{order_id} Нам важно ваше мнение – оцените в приложении!",
                'en': f"✅ Order delivered! 🧾 Order number: #{order_id} Your feedback matters – rate us in the app!"
            }
            should_send_sms_flag = False  # No SMS for COMPLETED as per the sheet
            sms_message = None

        elif order.status == 'CANCELLED':
            title = {
                'uz': "Buyurtma bekor qilindi",
                'ru': "Заказ отменён",
                'en': "Order cancelled",
            }
            message = {
                'uz': f"❌ Buyurtma bekor qilindi. 🧾 Buyurtma raqami: #{order_id}",
                'ru': f"❌ Заказ отменён. 🧾 Номер заказа: #{order_id}",
                'en': f"❌ Order cancelled. 🧾 Order number: #{order_id}"
            }
            should_send_sms_flag = True
            sms_message = {
                'uz': f"Buyurtma bekor qilindi (#{order_id}). – Carland.uz",
                'ru': f"Заказ отменён (#{order_id}). – Carland.uz",
                'en': f"Order cancelled (#{order_id}). – Carland.uz"
            }.get(lang)

        create_notification(
            content_object=order,
            notification_type=notification_type,
            context=context or {'order_id': order_id, 'status': order.status},
            title=title,
            message=message,
            user=order.user,
            should_send_sms=should_send_sms_flag,
            sms_message=sms_message
        )