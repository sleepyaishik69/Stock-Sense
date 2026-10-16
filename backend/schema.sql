-- StockSense AI empty SQLite schema. DDL and Alembic metadata only; no business/sample rows.
-- Apply with: python -m alembic upgrade head (this file is a schema snapshot).

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 2009a42c48a2

CREATE TABLE workspaces (
    id INTEGER NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    timezone VARCHAR(80) NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE data_imports (
    id INTEGER NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    imported_rows INTEGER NOT NULL, 
    rejected_rows INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_data_imports_workspace_id ON data_imports (workspace_id);

CREATE TABLE stores (
    id INTEGER NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_stores_workspace_id ON stores (workspace_id);

CREATE TABLE users (
    id INTEGER NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE data_import_errors (
    id INTEGER NOT NULL, 
    batch_id INTEGER NOT NULL, 
    row_number INTEGER NOT NULL, 
    message TEXT NOT NULL, 
    raw_row TEXT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(batch_id) REFERENCES data_imports (id)
);

CREATE INDEX ix_data_import_errors_batch_id ON data_import_errors (batch_id);

CREATE TABLE products (
    id INTEGER NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    store_id INTEGER NOT NULL, 
    sku VARCHAR(100) NOT NULL, 
    name VARCHAR(240) NOT NULL, 
    category VARCHAR(120) NOT NULL, 
    unit_price NUMERIC(14, 2) NOT NULL, 
    unit_cost NUMERIC(14, 2), 
    stock_on_hand INTEGER, 
    reorder_threshold INTEGER NOT NULL, 
    lead_time_days INTEGER, 
    archived BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(store_id) REFERENCES stores (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    CONSTRAINT uq_product_workspace_sku UNIQUE (workspace_id, sku)
);

CREATE INDEX ix_products_store_id ON products (store_id);

CREATE INDEX ix_products_workspace_id ON products (workspace_id);

CREATE TABLE sales (
    id INTEGER NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    store_id INTEGER NOT NULL, 
    product_id INTEGER NOT NULL, 
    transaction_id VARCHAR(120) NOT NULL, 
    sale_date DATE NOT NULL, 
    quantity INTEGER NOT NULL, 
    unit_price NUMERIC(14, 2) NOT NULL, 
    discount NUMERIC(14, 2) NOT NULL, 
    tax NUMERIC(14, 2) NOT NULL, 
    unit_cost NUMERIC(14, 2), 
    fingerprint VARCHAR(64) NOT NULL, 
    is_return BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(product_id) REFERENCES products (id), 
    FOREIGN KEY(store_id) REFERENCES stores (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    CONSTRAINT uq_sale_fingerprint UNIQUE (workspace_id, fingerprint)
);

CREATE INDEX ix_sales_product_id ON sales (product_id);

CREATE INDEX ix_sales_sale_date ON sales (sale_date);

CREATE INDEX ix_sales_store_id ON sales (store_id);

CREATE INDEX ix_sales_transaction_id ON sales (transaction_id);

CREATE INDEX ix_sales_workspace_date ON sales (workspace_id, sale_date);

CREATE INDEX ix_sales_workspace_id ON sales (workspace_id);

CREATE TABLE stock_movements (
    id INTEGER NOT NULL,
    workspace_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    movement_type VARCHAR(32) NOT NULL,
    quantity_delta INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    note VARCHAR(500),
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id),
    FOREIGN KEY(store_id) REFERENCES stores (id),
    FOREIGN KEY(product_id) REFERENCES products (id),
    FOREIGN KEY(actor_user_id) REFERENCES users (id)
);

CREATE INDEX ix_stock_movements_workspace_id ON stock_movements (workspace_id);
CREATE INDEX ix_stock_movements_store_id ON stock_movements (store_id);
CREATE INDEX ix_stock_movements_product_id ON stock_movements (product_id);
CREATE INDEX ix_stock_movements_created_at ON stock_movements (created_at);
CREATE INDEX ix_stock_movement_workspace_product_date ON stock_movements (workspace_id, product_id, created_at);

INSERT INTO alembic_version (version_num) VALUES ('7b5a22cc0e31') RETURNING version_num;

