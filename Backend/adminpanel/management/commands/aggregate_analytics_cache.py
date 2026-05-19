from django.core.management.base import BaseCommand

from adminpanel.tasks import aggregate_analytics_cache_task


class Command(BaseCommand):
    help = "Queue analytics cache aggregation task."

    def handle(self, *args, **options):
        result = aggregate_analytics_cache_task.delay()
        self.stdout.write(self.style.SUCCESS(f"Queued analytics aggregation task id={result.id}"))
