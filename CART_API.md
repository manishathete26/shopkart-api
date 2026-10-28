# Cart API

All cart endpoints require an access token. In Swagger, click **Authorize** and
enter the access token returned by `/auth/login` or `/auth/register`.

## Add a product variant

`POST /cart/items`

```json
{
  "parentId": 1,
  "variant_id": "1-1-awesome-iceblue-128-gb",
  "quantity": 1
}
```

`parentId` is the parent product's `id` (the API also accepts `parent_id`);
`variant_id` must match a variant's `variantid` in that product's `variants`
array. Adding the same variant again
increases its existing cart quantity. Requests exceeding current stock return
HTTP 409. When the same user has the same product variant in their wishlist,
adding it to the cart removes that wishlist entry in the same database
transaction. Other wishlist variants are left unchanged. The response includes
`wishlist_item_removed` to indicate whether a matching entry was removed.

## Read the cart

`GET /cart`

The response includes the authenticated user's items, each line total, total
quantity (`count`), and `cart_total`. Prices are read from the current product
catalog, so a catalog price change is reflected the next time the cart is read.

## Change quantity

`PATCH /cart/items/{item_id}`

```json
{
  "quantity": 2
}
```

## Remove an item

`DELETE /cart/items/{item_id}`

`item_id` is the cart row's `item_id` returned by `GET /cart` or
`POST /cart/items`. Each user's cart is isolated; a user cannot update or remove
another user's items.

## Move a wishlist item into the cart

`POST /wishlist/{product_id}/cart`

This uses the variant saved with that wishlist item, adds one to the cart (or
increases the matching cart line by one), and removes the item from the wishlist
in the same database transaction. The request requires an access token and has
no body. Alternatively, call `POST /cart/items` with the product and variant;
that endpoint also removes an exact matching wishlist entry. If the saved
variant is missing or stock is insufficient, the request returns an error and
leaves the wishlist item in place. If the item is already in the cart, its new
quantity must not exceed available stock or 99.

After reviewing the cart, place an order with `POST /orders`. A successful order
creation decrements stock, records the order, and clears the user's cart in one
transaction. Failed order validation leaves the cart unchanged.

The `cart_items` table stores the user, parent product, variant ID, and
quantity. Product and variant details remain in the existing `products` table.
