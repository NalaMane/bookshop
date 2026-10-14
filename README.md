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
git clone <REPO-URL>
cd bookshop
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_books          # adds 10 sample books
python manage.py createsuperuser     # your own admin login
python manage.py runserver
```

Open http://127.0.0.1:8000 · Admin: http://127.0.0.1:8000/admin

Run tests: `python manage.py test`

## Git workflow

```bash
git checkout main && git pull           # always start from the latest main
git checkout -b products                 # your branch: products / accounts / orders / ui
# ... work ...
git add . && git commit -m "Add search to book list"
git push -u origin products
```
Then open a **Pull Request** on GitHub → Nala reviews & merges.
Pull `main` into your branch every 1–2 days: `git pull origin main`.

If you change a `models.py`, run `python manage.py makemigrations` and commit the new migration file.

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

- **Django**: login, database (ORM) and admin are built in → we focus on shop logic.
- **SQLite**: zero setup, the database is one file.
- **One Django app per feature** → each person works in their own folder, almost no merge conflicts.
- **Cart in the session** → works without login; saved to the database only at checkout.
- **OrderItem stores name + price at purchase time** → history stays correct if a book's price changes or it is deleted.
- **Order status as fixed choices** (pending/shipped/completed) → no invalid values.
