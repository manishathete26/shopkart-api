# MySQL setup

The API uses SQLAlchemy and reads its database connection from `DATABASE_URL`.
Install MySQL Community Server, then create a database and application user in
MySQL (or through DBeaver):

```sql
CREATE DATABASE shopkart CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'shopkart_app'@'localhost' IDENTIFIED BY 'replace-with-a-strong-password';
GRANT ALL PRIVILEGES ON shopkart.* TO 'shopkart_app'@'localhost';
```

Set this environment variable for the API process, substituting your actual
credentials and host:

```text
DATABASE_URL=mysql+pymysql://shopkart_app:replace-with-a-strong-password@127.0.0.1:3306/shopkart?charset=utf8mb4
```

Do not commit real database passwords. Add the URL to your local `.env` file or
your hosting provider's environment variables. On startup, the API creates the
SQLAlchemy tables and imports `app/data/products.json` when the products table
is empty. Products, their variants, and wishlist items are stored in related
tables. The wishlist product foreign key is added on existing MySQL/PostgreSQL
databases when all existing wishlist product IDs match catalog products.

After changing the JSON catalog, synchronize it to the database with:

```bash
python -m app.scripts.seed_products
```

This explicit command refreshes product and variant rows from the JSON file.
