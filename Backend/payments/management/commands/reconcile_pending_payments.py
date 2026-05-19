from django.core.management.base import BaseCommand

from payments.tasks import reconcile_pending_payments_task


class Command(BaseCommand):
    help = "Queue pending payment reconciliation task."

    def handle(self, *args, **options):
        result = reconcile_pending_payments_task.delay()
        self.stdout.write(self.style.SUCCESS(f"Queued reconcile task id={result.id}"))
