-- Schema of the reporting replica, as exported by the platform team.
-- Row counts are the ones printed on the export; nobody has refreshed them since.

CREATE TABLE customers (
    customer_id   bigint PRIMARY KEY,
    email         text NOT NULL,
    full_name     text NOT NULL,
    country       text NOT NULL,
    created_at    timestamptz NOT NULL
);
-- approximate rows: 412,000

CREATE TABLE orders (
    order_id      bigint PRIMARY KEY,
    customer_id   bigint NOT NULL REFERENCES customers (customer_id),
    placed_at     timestamptz NOT NULL,
    channel       text NOT NULL,
    amount        numeric(12, 2) NOT NULL,
    status        text NOT NULL,
    note          text
);
-- approximate rows: unknown, "tens of millions"

CREATE TABLE order_lines (
    order_line_id bigint PRIMARY KEY,
    order_id      bigint NOT NULL REFERENCES orders (order_id),
    sku           text NOT NULL,
    quantity      integer NOT NULL,
    unit_price    numeric(12, 2) NOT NULL
);
-- approximate rows: unknown

-- There is no index on orders.note, and none on orders.channel.
CREATE INDEX orders_placed_at_idx ON orders (placed_at);
CREATE INDEX order_lines_order_id_idx ON order_lines (order_id);
