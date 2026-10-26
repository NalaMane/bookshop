# ERP sample files (Lab 2)

Test files for the ERP → web shop import. `valid_erp_export.xlsx` is a real export from the
Mini-ERP (Products app → Export button) with the bike demo data replaced by books, so the sheet,
columns and cell types are exactly what the ERP produces. The others use the same format.

| File | Expected result |
|---|---|
| `valid_erp_export.xlsx` | Real ERP export – 2 books imported (BOOK1002 The Hobbit, BOOK1001 1984) |
| `updated_erp_export.xlsx` | Changes in the ERP: BOOK1001 price 9.99 → 8.99, BOOK1002 out of stock, new book BOOK2001 (Dune) |
| `export_with_errors.xlsx` | 2 rows imported (BOOK1001, BOOK2002), 7 rows skipped with an error message each |
| `missing_columns.xlsx` | Whole file rejected: column Stock missing → `failed/` |
| `empty_export.xlsx` | Whole file rejected: no products |
| `wrong_format.txt` | Whole file rejected: wrong file type |
| `not_really_excel.xlsx` | Whole file rejected: can't be opened as Excel |
| `valid_export.csv` | CSV alternative (semicolon, German decimal comma) – 2 products imported |

Copy a file into `erp_exchange/inbox/` to test the import. Don't put new files in this folder
except test files – real transfers go through `inbox/`.
