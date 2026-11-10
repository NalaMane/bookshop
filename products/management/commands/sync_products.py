"""Lab 3 – load the book list from the ERP API (owner: Ami).

    python manage.py sync_products

Can be run by hand or by a scheduler (Task Scheduler / cron). The book list page
also does this automatically, see products/catalog.py.
"""
from django.core.management.base import BaseCommand, CommandError

from bookshop import erp_client as erp
from products.catalog import sync_catalog


class Command(BaseCommand):
    help = "Create / update the shop's books from the ERP (via the ERP API, no file)."

    def handle(self, *args, **options):
        try:
            created, updated = sync_catalog()
        except erp.ERPError as error:
            raise CommandError(f"ERP not available: {error.message}") from error
        self.stdout.write(self.style.SUCCESS(f"ERP catalog synced: {created} created, {updated} updated."))
