from products.models import Product


def import_rows(rows):
    created = 0
    updated = 0

    for row in rows:
        product, was_created = Product.objects.update_or_create(
            erp_id=row["erp_id"],
            defaults={
                "name": row["name"],
                "description": row["description"],
                "price": row["price"],
            "stock": row["stock"],
        }
    )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated

