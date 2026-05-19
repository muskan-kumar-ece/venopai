from django.core.management.base import BaseCommand

from orders.tasks import send_abandoned_cart_reminders_task


class Command(BaseCommand):
    help = "Send abandoned cart reminder emails for carts inactive for 2 hours."

    def handle(self, *args, **options):
        result = send_abandoned_cart_reminders_task.delay()
        self.stdout.write(self.style.SUCCESS(f"Queued abandoned cart reminder task id={result.id}."))
