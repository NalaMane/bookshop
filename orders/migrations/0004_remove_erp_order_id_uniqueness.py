from django.db import connection, migrations


def remove_erp_order_id_constraint(apps, schema_editor):
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            'ALTER TABLE "orders_order" '
            'DROP CONSTRAINT IF EXISTS "orders_order_erp_order_id_key"'
        )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_alter_order_erp_order_id"),
    ]

    operations = [
        migrations.RunPython(
            remove_erp_order_id_constraint,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
