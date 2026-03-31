from django.core.management.base import BaseCommand
from app.utils.notification_utils import create_oil_change_notifications, create_order_notifications
from config.firebase_config import initialize_firebase  # If using a dedicated module
from app.utils.notification_utils import create_oil_change_notifications  # Adjust import based on where your function is

class Command(BaseCommand):
    help = 'Send oil change notifications'

    def handle(self, *args, **kwargs):
        initialize_firebase()  # Ensure Firebase is initialized
        create_oil_change_notifications()
        create_order_notifications()
        self.stdout.write(self.style.SUCCESS('Successfully sent notifications'))