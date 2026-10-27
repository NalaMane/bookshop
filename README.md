# 📚 Online Book Shop – Lab 1 & Lab 2

Simple web shop built with **Python + Django + SQLite + Bootstrap**.

## Team & who owns what

| Person | Part | Folder(s) you work in |
|---|---|---|
| **Nala** | Setup & data | `bookshop/` (settings, main urls), models review, `seed_books` |
| **Svenja** | Products | `products/` |
| **Ami** | Customers | `accounts/` |
| **Agasi** | Cart & Orders | `orders/` |
| **GP** | UI, Testing, Presenting | `templates/base.html`, `static/`, all `tests.py`, slides |

**Rule:** only edit files in your own folder. Need a change somewhere else? Ask the owner.
`bookshop/settings.py` and `bookshop/urls.py` → ask Nala. `templates/base.html` → ask GP.

## Setup (first time)

```bash
git clone https://github.com/NalaMane/bookshop.git
cd bookshop
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
# create the .env file with the shared database link (see "Shared database" below)
python manage.py runserver
```

Open http://127.0.0.1:8000 · Admin: http://127.0.0.1:8000/admin

Logins (password `demo12345`): `staff` (admin) · `anna` (customer)

Run tests: `python manage.py test`

## Git workflow (no branches – everyone works in their own folder)

```bash
git pull                                # before you start
# ... work, then check the site still runs: python manage.py runserver
git add .
git commit -m "short description"
git pull                                # again, right before pushing
git push
```

Rules: only edit your own folder · only push if the site runs and `python manage.py test` says OK ·
changed a `models.py`? run `python manage.py makemigrations`, commit the new migration file, and read the
shared-database rules below before running `migrate` · git says "conflict"? don't force anything, message Nala.

## Demo data

`python manage.py seed_demo` adds 10 books with covers, 3 sample orders and two logins (password `demo12345`):
`staff` (admin – add/edit/delete books, change order status) and `anna` (customer with purchase history).
It is safe to run more than once. On the shared database it only needs to be run once, by one person.

## Shared database (PostgreSQL on Neon)

We all use **one shared database in the cloud**, so books, users and orders are the same for everyone.

**One-time setup on your PC:**
1. `pip install -r requirements.txt`
2. In the project folder (next to `manage.py`) create a file called **`.env`**
   (copy `.env.example` and rename the copy).
3. Put the real line in it – Nala sends it to you privately:
   `DATABASE_URL=postgresql://...`
4. `python manage.py runserver` – you are now on the shared database.

**Rules for the shared database:**
- Never push `.env` or paste the link anywhere public (it contains the password). `.env` is already in `.gitignore`.
- Changed a `models.py`? Tell the group **before** running `migrate`, and push your code right after –
  `migrate` changes the database for everyone.
- Don't delete other people's test data. Use your own test users.
- `python manage.py test` always uses a temporary local database, so tests never touch shared data.
- No `.env` file (or offline)? Django falls back to your own local `db.sqlite3`.

## Lab 2 – Product import from the ERP (file transfer)

The ERP (Mini-ERP from Lab 0) is the **master system for products**: books are created there,
exported as a file and imported into the shop. The shop never sends products back to the ERP.

```
ERP: Products → Export (.xlsx)  →  erp_exchange/inbox/  →  validate  →  import  →  books in the shop
                                                               │            │
                                                     ImportLog in /admin    file moved to processed/ or failed/
```

**How to import**
- In the shop (staff only): navbar → **Import ERP file** → upload the export → result is shown.
- Or: put the file into `erp_exchange/inbox/` and run `python manage.py import_products`.
- Test files: `erp_exchange/samples/` (README there explains each one).

**Rules**
- The **ERP product ID** is stored as `erp_id` and links both systems. In the ERP we use the **ISBN**
  as Product ID, e.g. `9780547928227` for The Hobbit.
- Import: product with this `erp_id` exists → update; otherwise an old book with the same name and no
  `erp_id` is linked (only if exactly one matches); otherwise a new book is created.
- The ERP decides name, price and stock. Author and cover are shop-only and never overwritten; the
  description is only replaced when the ERP sends one.
- **Content Enricher:** if the Product ID is an ISBN and the book has no cover, the cover is added from Open Library.
- **No stock = can't be bought.** A book needs a stock number to be sold; stock goes down after each order.
- Errors: a wrong file type, an unreadable file or missing columns reject the **whole file** (→ `failed/`);
  a bad row (e.g. price "abc") is **skipped**, the other rows are imported. Everything is listed in
  **/admin → Import logs**. The import of one file is all-or-nothing (one transaction).
- Files are renamed `products_YYYY-MM-DD_HHMMSS.xlsx` when they are moved, so nothing is imported twice
  and every transfer is kept.

**Known limitations of file transfer (for the presentation)**
- Not real-time: between two imports the shop can show an old price or stock.
- One-way: sales in the shop are not reported to the ERP, so the next import sets the stock back to the ERP value.
- Books deleted in the ERP stay in the shop (they are just missing from the next file).
- Improvement: automatic import (e.g. every 15 min) or – better – a direct API / messaging connection (next labs).

| Lab 2 part | Owner | Files |
|---|---|---|
| Setup (`erp_id`, `stock`, folders) | Nala | `products/models.py`, `bookshop/settings.py` |
| Import into the shop | Svenja | `erp_import/importer.py`, `erp_import/management/commands/import_products.py` |
| Validation, ImportLog, file handling, sample files | Ami | `erp_import/validation.py`, `models.py`, `files.py`, `erp_exchange/samples/` |
| Stock in cart and checkout | Agasi | `orders/` |
| Upload page, tests, slides | GP | `erp_import/views.py`, `templates/`, `erp_import/tests.py` |

## Structure

```
bookshop/           project settings + main URLs (Nala)
products/           Product model, list/detail/add/edit/delete (Svenja)
accounts/           Profile model, register/login/logout/profile/history (Ami)
orders/             Order + OrderItem models, session cart, checkout (Agasi)
  cart.py           cart logic (stored in the session)
templates/base.html shared layout + navbar (GP)
static/css/         custom CSS (GP)
```

## Data model

- **Product**: name, author, description, price
- **User** (Django built-in): username, first/last name, email, password
- **Profile**: user (1–1), address
- **Order**: customer, created_at, status (pending / shipped / completed), shipping_address, total_price
- **OrderItem**: order, product, product_name, unit_price, quantity
- Purchase history = `user.orders`

## Features already working (basic versions – improve them!)

- Book list, detail; staff can add / edit / delete books
- Register, log in, log out, edit profile, purchase history
- Cart: add, +/− quantity, remove; checkout creates an order
- Staff change order status in Admin → Orders

## Design decisions (for the presentation)

- **Shared PostgreSQL database in the cloud (Neon)**: the whole team works on the same data; the password is kept out of GitHub in a `.env` file; tests run on a separate local SQLite database so they can never damage shared data.
- **Django**: login, database (ORM) and admin are built in → we focus on shop logic.
- **SQLite** as fallback and for tests: zero setup, works offline.
- **One Django app per feature** → each person works in their own folder, almost no merge conflicts.
- **Cart in the session** → works without login; saved to the database only at checkout.
- **OrderItem stores name + price at purchase time** → history stays correct if a book's price changes or it is deleted.
- **Order status as fixed choices** (pending/shipped/completed) → no invalid values.
