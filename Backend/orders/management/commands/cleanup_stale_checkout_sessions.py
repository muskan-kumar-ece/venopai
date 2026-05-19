from django.core.management.base import BaseCommand
from orders.tasks import cleanup_stale_checkout_sessions_task


class Command(BaseCommand):
    help = "Release expired inventory reservations and cancel stale pending-payment orders."

    def handle(self, *args, **options):
        result = cleanup_stale_checkout_sessions_task.delay()
        self.stdout.write(self.style.SUCCESS(f"Queued checkout cleanup task id={result.id}."))
