# 📚 Campus Swap — Book & Belongings Exchange Platform

A simple Flask + MySQL + Jinja2 marketplace where students can list, browse,
and swap books and belongings within their campus.

## Tech stack
- **Backend:** Python, Flask, Flask sessions
- **Templates:** Jinja2 (your original `index.html`, `login.html`,
  `register.html`, `profile.html` — wired up, not redesigned)
- **Database:** MySQL, plain SQL via `mysql-connector-python` (no ORM)
- **Security:** Werkzeug password hashing, session-based auth, seller-only
  edit/delete checks

## Project structure
```
campus_swap/
├── app.py               
├── schema.sql           
├── requirements.txt
├── templates/
│   ├── index.html         
│   ├── login.html          
│   ├── register.html       
│   ├── profile.html        
│   ├── marketplace.html   
│   ├── item_detail.html   
│   ├── add_item.html     
│   ├── edit_item.html      
│   └── my_listings.html   
└── static/
    └── assets/css, assets/js  
```

Your 4 uploaded pages were **not redesigned**. The only changes made to them
were the minimum needed to make them functional:
- static asset paths (`assets/...` → `/static/assets/...`)
- internal links pointed at real Flask routes instead of dead `.html` files
- the "Account" menu and "List an Item" button now show the right options
  depending on whether someone is signed in
- the login/register/profile forms got `name=` attributes, a `method="POST"`,
  and real values pulled from the database

`index.html` is a marketing/landing page in the theme you provided — it has
no listing grid, and there was no item-detail, add-item, edit-item, or
"my listings" page in your upload. Those five pages are new, built in the
same Bootstrap theme/style so they look consistent with your pages.

## 1. Set up the database
```bash
mysql -u root -p < schema.sql
```
This creates a `campus_swap` database with two tables:
- `users` — student accounts (name, email, password hash, campus/hostel/
  department details)
- `items` — listings, each with a `seller_id` foreign key to `users` (1
  user → many items, `ON DELETE CASCADE`)

## 2. Configure environment variables (optional)
The app defaults to `root` with no password on `localhost`. To use a
dedicated app user instead:
```bash
export DB_HOST=localhost
export DB_USER=campus_app
export DB_PASSWORD=your_password
export DB_NAME=campus_swap
export SECRET_KEY=some-random-string
```

## 3. Install dependencies & run
```bash
pip install -r requirements.txt
python app.py
```
Visit **http://localhost:5000**

## Routes
| Route | Method | Description |
|---|---|---|
| `/` | GET | Homepage |
| `/marketplace` | GET | Browse/search all listings (`?category=`, `?q=`) |
| `/item/<id>` | GET | Item detail + seller info |
| `/register` | GET/POST | Create account |
| `/login` | GET/POST | Sign in |
| `/logout` | GET | Sign out |
| `/profile` | GET | Account details (login required) |
| `/profile/basic` | POST | Update name/email/phone/bio |
| `/profile/campus` | POST | Update campus/hostel/department/etc. |
| `/profile/delete` | POST | Delete account (cascades to their listings) |
| `/my-listings` | GET | A user's own listings |
| `/add-item` | GET/POST | Create a listing (login required) |
| `/edit-item/<id>` | GET/POST | Edit a listing (owner only) |
| `/delete-item/<id>` | POST | Delete a listing (owner only) |

## Notes
- Your uploaded theme has no image assets (`assets/img/...` was referenced
  but never included), so logo/avatar/hero images will show as broken —
  drop real image files into `static/assets/img/` to fix that.
- This has been tested end-to-end against a real MySQL/MariaDB instance:
  register → login → edit profile → list an item → browse → edit → delete,
  plus ownership checks (a user can't edit/delete another student's listing)
  and duplicate-email rejection.
