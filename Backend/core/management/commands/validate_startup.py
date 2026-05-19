from django.core.management.base import BaseCommand

from core.env_validation import validate_environment
from core.health import _run_checks


class Command(BaseCommand):
    help = "Validate environment and startup readiness checks."

    def handle(self, *args, **options):
        issues = validate_environment()
        checks, degraded = _run_checks(include_external=True)

        for issue in issues:
            writer = self.stderr if issue.level == "error" else self.stdout
            writer.write(f"[{issue.level.upper()}] {issue.key}: {issue.message}")

        self.stdout.write(f"Health checks: {checks}")
        has_error = any(issue.level == "error" for issue in issues)
        if degraded or has_error:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Startup validation passed."))
