from django.core.management.base import BaseCommand

from payments.tasks import retry_webhook_processing_task


class Command(BaseCommand):
    help = "Queue webhook retry processing task."

    def handle(self, *args, **options):
        result = retry_webhook_processing_task.delay()
        self.stdout.write(self.style.SUCCESS(f"Queued webhook retry task id={result.id}"))
