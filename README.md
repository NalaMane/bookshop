# 📚 Online Book Shop – Lab 1

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
