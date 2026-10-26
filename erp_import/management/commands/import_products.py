from django.core.management.base import BaseCommand

from erp_import.files import inbox_files, move_file, PROCESSED, FAILED
from erp_import.importer import import_rows
from erp_import.models import ImportLog
from erp_import.validation import read_and_validate, InvalidFileError


class Command(BaseCommand):
    def handle(self, *args, **options):
        for path in inbox_files():
            try:
                rows, errors = read_and_validate(path)

            except InvalidFileError as error:
                ImportLog.record(
                    path.name,
                    file_error=str(error),
                )
                move_file(path, FAILED)
                self.stdout.write(
                    f"{path.name}: failed - {error}"
                )
                continue

            created, updated = import_rows(rows)
            self.stdout.write(
                f"{path.name}: {created} created, {updated} updated, {len(errors)} failed rows"
            )

            ImportLog.record(
                path.name,
                created,
                updated,
                errors,
            )

            move_file(path, PROCESSED)