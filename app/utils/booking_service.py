from datetime import timedelta
from django.utils.timezone import now
from app.tasks import send_booking_reminder
import logging

logger = logging.getLogger(__name__)

def schedule_booking_reminders(booking):
    one_day_eta = booking.start_time - timedelta(days=1)
    two_hour_eta = booking.start_time - timedelta(hours=2)
    if one_day_eta > now():
        logger.warning("One day eta: %s", one_day_eta)
        send_booking_reminder.apply_async((booking.id, "1_day"), eta=one_day_eta)
    if two_hour_eta > now():
        logger.warning("Two hour eta: %s", two_hour_eta)
        send_booking_reminder.apply_async((booking.id, "2_hours"), eta=two_hour_eta)
