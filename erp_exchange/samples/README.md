# ERP sample files (Lab 2)

Test files for the ERP → web shop import. `valid_erp_export.xlsx` is a real export from the
Mini-ERP (Products app → Export button) with the bike demo data replaced by books (Product ID = ISBN, like in our ERP), so the sheet,
columns and cell types are exactly what the ERP produces. The others use the same format.

| File | Expected result |
|---|---|
| `valid_erp_export.xlsx` | Real ERP export – 2 books imported (The Hobbit 9780547928227, 1984 9780451524935) |
| `updated_erp_export.xlsx` | Changes in the ERP: 9780451524935 price 9.99 → 8.99, 9780547928227 out of stock, new book 9780441172719 (Dune) |
| `export_with_errors.xlsx` | 2 rows imported (9780451524935, 9780141439518), 7 rows skipped with an error message each |
| `missing_columns.xlsx` | Whole file rejected: column Stock missing → `failed/` |
| `empty_export.xlsx` | Whole file rejected: no products |
| `wrong_format.txt` | Whole file rejected: wrong file type |
| `not_really_excel.xlsx` | Whole file rejected: can't be opened as Excel |
| `valid_export.csv` | CSV alternative (semicolon, German decimal comma) – 2 products imported |

Copy a file into `erp_exchange/inbox/` to test the import. Don't put new files in this folder
except test files – real transfers go through `inbox/`.
