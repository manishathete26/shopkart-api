# Cart API

All cart endpoints require an access token. In Swagger, click **Authorize** and
enter the access token returned by `/auth/login` or `/auth/register`.

## Add a product variant

`POST /cart/items`

```json
{
  "product_id": 1,
  "variant_id": "1-1-awesome-iceblue-128-gb",
  "quantity": 1
}
```

`product_id` is the parent product's `id`; `variant_id` must match a variant's
`variantid` in that product's `variants` array. Adding the same variant again
increases its existing cart quantity. Requests exceeding current stock return
HTTP 409.

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

The `cart_items` table stores the user, parent product, variant ID, and
quantity. Product and variant details remain in the existing `products` table.
