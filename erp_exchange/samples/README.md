# ERP sample files (Lab 2)

Test files for the ERP → web shop import. `valid_erp_export.xlsx` is a real export from the
Mini-ERP (Products app → Export button). The others are based on the same format.

| File | Expected result |
|---|---|
| `valid_erp_export.xlsx` | Real ERP export – 2 products imported (GRVL1000, DXTR1000) |
| `updated_erp_export.xlsx` | Changes in the ERP: DXTR1000 price 1200 → 1100, GRVL1000 out of stock, new product ROAD2000 |
| `export_with_errors.xlsx` | 2 rows imported (DXTR1000, TREK1000), 7 rows skipped with an error message each |
| `missing_columns.xlsx` | Whole file rejected: column Stock missing → `failed/` |
| `empty_export.xlsx` | Whole file rejected: no products |
| `wrong_format.txt` | Whole file rejected: wrong file type |
| `not_really_excel.xlsx` | Whole file rejected: can't be opened as Excel |
| `valid_export.csv` | CSV alternative (semicolon, German decimal comma) – 2 products imported |

Copy a file into `erp_exchange/inbox/` to test the import. Don't put new files in this folder
except test files – real transfers go through `inbox/`.
