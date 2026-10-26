"""Staff-only upload page for ERP files (owner: GP).

Flow: upload file -> save to erp_exchange/inbox/ -> run the import_products
command (Svenja + Ami) -> show the result.
The file type is NOT checked here: Ami's read_and_validate() is the single place
that rejects wrong files, and the rejection shows up in the ImportLog.
"""
import io
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command
from django.shortcuts import render
from django.utils.text import get_valid_filename

try:  # ImportLog is written by Ami; the page still works without it
    from .models import ImportLog
except ImportError:
    ImportLog = None

MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@staff_member_required(login_url="accounts:login")
def upload(request):
    context = {}

    if request.method == "POST":
        erp_file = request.FILES.get("erp_file")

        if erp_file is None:
            messages.error(request, "Please choose a file first.")
        elif erp_file.size > MAX_SIZE:
            messages.error(request, "The file is too large (maximum 5 MB).")
        else:
            inbox = Path(settings.ERP_EXCHANGE_DIR) / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            saved_name = f"{stamp}_{get_valid_filename(erp_file.name)}"

            with open(inbox / saved_name, "wb") as target:
                for chunk in erp_file.chunks():
                    target.write(chunk)

            output = io.StringIO()
            try:
                call_command("import_products", stdout=output)
                messages.success(request, "Import finished.")
            except Exception as exc:  # show the problem instead of a crash page
                messages.error(request, f"Import failed: {exc}")

            context["file_name"] = saved_name
            context["output"] = output.getvalue()
            if ImportLog is not None:
                context["log"] = ImportLog.objects.order_by("-id").first()

    return render(request, "erp_import/upload.html", context)
