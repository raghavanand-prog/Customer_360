"""Initial Customer360 serving schema (§12).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-22
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


DDL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================== CORE DOMAIN

CREATE TABLE customers (
    canonical_customer_id   TEXT PRIMARY KEY,
    first_name              TEXT,
    last_name               TEXT,
    full_name_display       TEXT,
    primary_email           TEXT,
    primary_phone           TEXT,
    city                    TEXT,
    state                   TEXT,
    country_code            CHAR(2),
    account_status          TEXT CHECK (account_status IN ('active','inactive','churned','unknown')) DEFAULT 'unknown',
    source_system_count     SMALLINT NOT NULL DEFAULT 0,
    identity_confidence     NUMERIC(4,3) CHECK (identity_confidence IS NULL OR identity_confidence BETWEEN 0 AND 1),
    needs_review            BOOLEAN NOT NULL DEFAULT FALSE,
    last_activity_at        TIMESTAMPTZ,
    last_updated_run_id     BIGINT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_customers_name_trgm ON customers USING GIN (full_name_display gin_trgm_ops);
CREATE INDEX ix_customers_country ON customers (country_code);

CREATE TABLE customer_identities (
    identity_id             BIGSERIAL PRIMARY KEY,
    canonical_customer_id   TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    identity_namespace      TEXT NOT NULL,
    identity_value_norm     TEXT,
    identity_value_hash     TEXT NOT NULL,
    identity_value_masked   TEXT,
    source_system           TEXT NOT NULL,
    source_record_id        TEXT NOT NULL,
    linked_by_rule          TEXT,
    confidence              NUMERIC(4,3),
    is_primary              BOOLEAN NOT NULL DEFAULT FALSE,
    is_screened             BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (identity_namespace, identity_value_hash, source_system, source_record_id)
);
CREATE INDEX ix_cust_ident_ns_hash ON customer_identities (identity_namespace, identity_value_hash);
CREATE INDEX ix_cust_ident_customer ON customer_identities (canonical_customer_id);
CREATE UNIQUE INDEX ux_cust_ident_primary ON customer_identities (canonical_customer_id, identity_namespace)
    WHERE is_primary;

CREATE TABLE customer_metrics (
    canonical_customer_id       TEXT PRIMARY KEY REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    as_of_date                  DATE NOT NULL,
    order_count                 INTEGER NOT NULL DEFAULT 0 CHECK (order_count >= 0),
    total_spend                 NUMERIC(14,2) NOT NULL DEFAULT 0,
    refunded_amount              NUMERIC(14,2) NOT NULL DEFAULT 0,
    aov                         NUMERIC(14,2) CHECK (aov IS NULL OR aov >= 0),
    first_order_at               TIMESTAMPTZ,
    last_order_at                TIMESTAMPTZ,
    days_since_last_order        INTEGER,
    median_ipi_days              NUMERIC(8,2),
    purchase_frequency_per_year  NUMERIC(8,3),
    historical_clv               NUMERIC(14,2) NOT NULL DEFAULT 0,
    forward_clv_heuristic         NUMERIC(14,2),
    r_score                      SMALLINT,
    f_score                      SMALLINT,
    m_score                      SMALLINT,
    rfm_segment                  TEXT,
    sessions_30d                 INTEGER NOT NULL DEFAULT 0,
    sessions_90d                 INTEGER NOT NULL DEFAULT 0,
    events_30d                   INTEGER NOT NULL DEFAULT 0,
    events_90d                   INTEGER NOT NULL DEFAULT 0,
    days_since_last_seen         INTEGER,
    cart_abandon_sessions_90d    INTEGER NOT NULL DEFAULT 0,
    engagement_raw                NUMERIC(10,4),
    engagement_score              SMALLINT,
    churn_risk_band                TEXT CHECK (churn_risk_band IN
        ('no_purchase_history','active','at_risk','churned')),
    preferred_category_id          TEXT,
    tenure_days                    INTEGER
);
CREATE INDEX ix_metrics_churn_band ON customer_metrics (churn_risk_band, days_since_last_order);
CREATE INDEX ix_metrics_spend ON customer_metrics (total_spend DESC);
CREATE INDEX ix_metrics_last_activity ON customer_metrics (as_of_date, days_since_last_order);

CREATE TABLE customer_field_provenance (
    provenance_id            BIGSERIAL PRIMARY KEY,
    canonical_customer_id    TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    field_name               TEXT NOT NULL,
    winning_value            TEXT,
    winning_source_system    TEXT,
    winning_source_record_id TEXT,
    alternative_values       JSONB,
    precedence_reason        TEXT,
    UNIQUE (canonical_customer_id, field_name)
);
CREATE INDEX ix_provenance_customer ON customer_field_provenance (canonical_customer_id);

CREATE TABLE products (
    product_id      TEXT PRIMARY KEY,
    sku             TEXT,
    product_name    TEXT NOT NULL,
    category_id     TEXT NOT NULL,
    category_name   TEXT NOT NULL,
    brand           TEXT,
    unit_price      NUMERIC(12,2) NOT NULL,
    currency        CHAR(3) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    stock_qty       INTEGER,
    launched_on     DATE
);
CREATE UNIQUE INDEX ux_products_sku ON products (sku) WHERE sku IS NOT NULL;
CREATE INDEX ix_products_category ON products (category_id);

CREATE TABLE orders (
    order_id                     TEXT PRIMARY KEY,
    canonical_customer_id        TEXT REFERENCES customers(canonical_customer_id) ON DELETE SET NULL,
    source_customer_ref          TEXT,
    source_customer_ref_type     TEXT,
    order_ts                     TIMESTAMPTZ NOT NULL,
    order_status                 TEXT NOT NULL,
    order_type                   TEXT NOT NULL CHECK (order_type IN ('sale','refund')),
    currency                     CHAR(3) NOT NULL,
    gross_amount                 NUMERIC(12,2) NOT NULL,
    discount_amount               NUMERIC(12,2) NOT NULL DEFAULT 0,
    shipping_amount               NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount                    NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_amount                    NUMERIC(12,2) NOT NULL,
    revenue_amount                NUMERIC(12,2) NOT NULL,
    payment_method                 TEXT,
    channel                       TEXT,
    is_first_order                 BOOLEAN NOT NULL DEFAULT FALSE,
    days_since_previous_order      INTEGER,
    item_count                    SMALLINT NOT NULL DEFAULT 0,
    ingested_run_id                BIGINT
);
CREATE INDEX ix_orders_customer_ts ON orders (canonical_customer_id, order_ts DESC);
CREATE INDEX ix_orders_ts_brin ON orders USING BRIN (order_ts);

CREATE TABLE order_items (
    order_id            TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    line_number         SMALLINT NOT NULL,
    product_id          TEXT REFERENCES products(product_id) ON DELETE SET NULL,
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    unit_price          NUMERIC(12,2) NOT NULL,
    line_discount       NUMERIC(12,2) NOT NULL DEFAULT 0,
    line_net_amount     NUMERIC(12,2) NOT NULL,
    is_orphan_product   BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (order_id, line_number)
);
CREATE INDEX ix_order_items_product ON order_items (product_id);

CREATE TABLE sessions (
    session_id              TEXT PRIMARY KEY,
    canonical_customer_id   TEXT REFERENCES customers(canonical_customer_id) ON DELETE SET NULL,
    device_cookie           TEXT,
    session_start_ts        TIMESTAMPTZ NOT NULL,
    session_end_ts          TIMESTAMPTZ NOT NULL,
    duration_s              INTEGER NOT NULL CHECK (duration_s >= 0),
    event_count             INTEGER NOT NULL DEFAULT 0,
    distinct_pages          INTEGER NOT NULL DEFAULT 0,
    has_add_to_cart         BOOLEAN NOT NULL DEFAULT FALSE,
    has_checkout_start      BOOLEAN NOT NULL DEFAULT FALSE,
    has_purchase            BOOLEAN NOT NULL DEFAULT FALSE,
    is_bounce               BOOLEAN NOT NULL DEFAULT FALSE,
    entry_page              TEXT,
    utm_source              TEXT,
    CHECK (session_end_ts >= session_start_ts)
);
CREATE INDEX ix_sessions_customer_start ON sessions (canonical_customer_id, session_start_ts DESC);

CREATE TABLE web_events (
    event_id                TEXT PRIMARY KEY,
    canonical_customer_id   TEXT REFERENCES customers(canonical_customer_id) ON DELETE SET NULL,
    session_id              TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
    device_cookie           TEXT,
    event_type              TEXT NOT NULL,
    event_ts                TIMESTAMPTZ NOT NULL,
    page_url                TEXT,
    product_id              TEXT REFERENCES products(product_id) ON DELETE SET NULL,
    search_term             TEXT,
    cart_value              NUMERIC(12,2),
    utm_source              TEXT,
    utm_campaign            TEXT,
    device_type             TEXT,
    is_bot_suspected        BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_events_customer_ts ON web_events (canonical_customer_id, event_ts DESC);
CREATE INDEX ix_events_session ON web_events (session_id);
CREATE INDEX ix_events_product_type ON web_events (product_id, event_type);
CREATE INDEX ix_events_ts_brin ON web_events USING BRIN (event_ts);

CREATE TABLE anonymous_events (
    event_id       TEXT PRIMARY KEY,
    device_cookie  TEXT NOT NULL,
    event_type     TEXT NOT NULL,
    event_ts       TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_anon_events_cookie ON anonymous_events (device_cookie, event_ts DESC);

CREATE TABLE support_tickets (
    ticket_id                TEXT PRIMARY KEY,
    canonical_customer_id    TEXT REFERENCES customers(canonical_customer_id) ON DELETE SET NULL,
    order_id                 TEXT REFERENCES orders(order_id) ON DELETE SET NULL,
    requester_email_masked   TEXT,
    category                 TEXT NOT NULL,
    priority                 TEXT NOT NULL,
    status                   TEXT NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL,
    first_response_at        TIMESTAMPTZ,
    resolved_at              TIMESTAMPTZ,
    satisfaction_score       SMALLINT CHECK (satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 5)
);
CREATE INDEX ix_tickets_customer ON support_tickets (canonical_customer_id, created_at DESC);

CREATE TABLE marketing_events (
    marketing_event_id       BIGSERIAL PRIMARY KEY,
    canonical_customer_id    TEXT REFERENCES customers(canonical_customer_id) ON DELETE SET NULL,
    campaign_id              TEXT NOT NULL,
    campaign_name            TEXT,
    channel                  TEXT NOT NULL,
    event_type               TEXT NOT NULL,
    event_ts                 TIMESTAMPTZ NOT NULL,
    product_id               TEXT REFERENCES products(product_id) ON DELETE SET NULL
);
CREATE INDEX ix_mkt_customer_ts ON marketing_events (canonical_customer_id, event_ts DESC);

-- ===================================================== ANALYTICAL / SERVING

CREATE TABLE customer_category_affinity (
    canonical_customer_id   TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    category_id             TEXT NOT NULL,
    affinity_share          NUMERIC(6,5),
    view_share              NUMERIC(6,5),
    purchase_share          NUMERIC(6,5),
    last_interaction_at     TIMESTAMPTZ,
    PRIMARY KEY (canonical_customer_id, category_id)
);

CREATE TABLE product_co_purchase (
    product_id_a    TEXT NOT NULL,
    product_id_b    TEXT NOT NULL,
    co_order_count  INTEGER NOT NULL,
    lift            NUMERIC(10,4),
    PRIMARY KEY (product_id_a, product_id_b)
);

CREATE TABLE agg_revenue_daily (
    revenue_date       DATE PRIMARY KEY,
    order_count        INTEGER NOT NULL DEFAULT 0,
    revenue_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,
    unique_buyers       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE agg_revenue_monthly (
    revenue_month           DATE PRIMARY KEY,
    order_count             INTEGER NOT NULL DEFAULT 0,
    revenue_amount           NUMERIC(16,2) NOT NULL DEFAULT 0,
    unique_buyers            INTEGER NOT NULL DEFAULT 0,
    new_customer_revenue     NUMERIC(16,2) NOT NULL DEFAULT 0,
    returning_customer_revenue NUMERIC(16,2) NOT NULL DEFAULT 0
);

CREATE TABLE agg_cohort_retention (
    cohort_month    DATE NOT NULL,
    month_offset    INTEGER NOT NULL,
    active_customers INTEGER NOT NULL DEFAULT 0,
    revenue          NUMERIC(16,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (cohort_month, month_offset)
);

CREATE TABLE agg_product_performance (
    product_id           TEXT PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    units_sold           INTEGER NOT NULL DEFAULT 0,
    revenue              NUMERIC(16,2) NOT NULL DEFAULT 0,
    distinct_buyers       INTEGER NOT NULL DEFAULT 0,
    view_count            INTEGER NOT NULL DEFAULT 0,
    view_to_cart_rate      NUMERIC(6,5),
    cart_to_purchase_rate  NUMERIC(6,5),
    return_rate            NUMERIC(6,5)
);

CREATE TABLE agg_category_performance (
    category_id          TEXT PRIMARY KEY,
    category_name        TEXT,
    units_sold           INTEGER NOT NULL DEFAULT 0,
    revenue              NUMERIC(16,2) NOT NULL DEFAULT 0,
    revenue_share         NUMERIC(6,5)
);

CREATE TABLE customer_event_metrics (
    canonical_customer_id      TEXT PRIMARY KEY REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    sessions_30d               INTEGER NOT NULL DEFAULT 0,
    sessions_90d               INTEGER NOT NULL DEFAULT 0,
    sessions_365d              INTEGER NOT NULL DEFAULT 0,
    events_30d                 INTEGER NOT NULL DEFAULT 0,
    events_90d                 INTEGER NOT NULL DEFAULT 0,
    events_365d                INTEGER NOT NULL DEFAULT 0,
    avg_session_duration_s      NUMERIC(10,2),
    bounce_rate                 NUMERIC(6,5),
    last_seen_at                TIMESTAMPTZ,
    distinct_categories_viewed   INTEGER NOT NULL DEFAULT 0,
    cart_abandon_sessions        INTEGER NOT NULL DEFAULT 0
);

-- ================================================= OPERATIONAL / METADATA

CREATE TABLE pipeline_runs (
    run_id            BIGSERIAL PRIMARY KEY,
    pipeline_name     TEXT NOT NULL DEFAULT 'c360_pipeline',
    dataset_size      TEXT,
    status            TEXT NOT NULL CHECK (status IN ('running','succeeded','failed')),
    triggered_by      TEXT,
    code_version      TEXT,
    config_hash       TEXT,
    dq_ruleset_hash   TEXT,
    retry_of          BIGINT,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    duration_ms       INTEGER,
    error_summary     TEXT
);

CREATE TABLE pipeline_stage_runs (
    stage_run_id       BIGSERIAL PRIMARY KEY,
    run_id             BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    stage_name         TEXT NOT NULL,
    stage_order        SMALLINT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN ('pending','running','succeeded','failed','skipped')),
    rows_in            BIGINT,
    rows_out           BIGINT,
    rows_quarantined   BIGINT,
    rows_rejected      BIGINT,
    started_at         TIMESTAMPTZ,
    finished_at        TIMESTAMPTZ,
    duration_ms        INTEGER,
    metrics            JSONB,
    error_message      TEXT
);
CREATE INDEX ix_stage_runs_run ON pipeline_stage_runs (run_id, stage_order);

CREATE TABLE ingestion_files (
    file_id            BIGSERIAL PRIMARY KEY,
    run_id             BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    dataset            TEXT NOT NULL,
    file_name          TEXT NOT NULL,
    file_sha256        TEXT NOT NULL,
    bytes              BIGINT,
    rows_read          BIGINT,
    rows_unparseable   BIGINT NOT NULL DEFAULT 0,
    status             TEXT NOT NULL CHECK (status IN ('succeeded','failed','skipped')),
    ingested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset, file_sha256)
);

CREATE TABLE data_quality_results (
    dq_result_id         BIGSERIAL PRIMARY KEY,
    run_id               BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    dataset              TEXT NOT NULL,
    records_ingested     BIGINT NOT NULL DEFAULT 0,
    records_accepted     BIGINT NOT NULL DEFAULT 0,
    records_warned       BIGINT NOT NULL DEFAULT 0,
    records_quarantined  BIGINT NOT NULL DEFAULT 0,
    records_rejected     BIGINT NOT NULL DEFAULT 0,
    score_completeness   NUMERIC(5,2),
    score_validity       NUMERIC(5,2),
    score_uniqueness     NUMERIC(5,2),
    score_consistency    NUMERIC(5,2),
    score_integrity      NUMERIC(5,2),
    score_timeliness     NUMERIC(5,2),
    score_overall        NUMERIC(5,2),
    ruleset_hash         TEXT,
    UNIQUE (run_id, dataset)
);

CREATE TABLE data_quality_rule_results (
    rule_result_id            BIGSERIAL PRIMARY KEY,
    dq_result_id              BIGINT NOT NULL REFERENCES data_quality_results(dq_result_id) ON DELETE CASCADE,
    rule_id                   TEXT NOT NULL,
    rule_name                 TEXT NOT NULL,
    dimension                 TEXT NOT NULL,
    severity                  TEXT NOT NULL,
    records_applicable        BIGINT NOT NULL DEFAULT 0,
    records_passed            BIGINT NOT NULL DEFAULT 0,
    records_failed            BIGINT NOT NULL DEFAULT 0,
    failure_rate              NUMERIC(6,5),
    dataset_threshold_breached BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_dq_rule_results_result ON data_quality_rule_results (dq_result_id);

CREATE TABLE quarantined_records (
    quarantine_id        TEXT PRIMARY KEY,
    run_id               BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    dataset              TEXT NOT NULL,
    source_system        TEXT,
    source_file          TEXT,
    source_row_num       BIGINT,
    dq_status            TEXT NOT NULL CHECK (dq_status IN ('quarantined','rejected')),
    failed_rules         JSONB NOT NULL,
    record_payload       JSONB NOT NULL,
    record_hash          TEXT NOT NULL,
    first_seen_run_id    BIGINT,
    times_seen           INTEGER NOT NULL DEFAULT 1,
    remediation_status   TEXT NOT NULL DEFAULT 'new'
        CHECK (remediation_status IN ('new','acknowledged','fixed_at_source','wont_fix')),
    canonical_customer_id TEXT
);
CREATE INDEX ix_quarantine_lookup ON quarantined_records (run_id, dataset, dq_status);
CREATE INDEX ix_quarantine_rules ON quarantined_records USING GIN (failed_rules jsonb_path_ops);

CREATE TABLE dedup_audit (
    dedup_id              BIGSERIAL PRIMARY KEY,
    run_id                BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    entity                TEXT NOT NULL,
    strategy_id           TEXT NOT NULL,
    dedup_key             TEXT NOT NULL,
    kept_record_id        TEXT,
    copies_dropped        INTEGER NOT NULL DEFAULT 0,
    conflicting_payloads  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE identity_merge_audit (
    audit_id               BIGSERIAL PRIMARY KEY,
    run_id                 BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    event                  TEXT NOT NULL,
    canonical_customer_id  TEXT,
    related_canonical_ids  TEXT,
    source_record_key_a    TEXT,
    source_record_key_b    TEXT,
    rule_id                TEXT,
    namespace              TEXT,
    value_masked           TEXT,
    confidence             NUMERIC(4,3),
    occurred_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_identity_audit_customer ON identity_merge_audit (canonical_customer_id);

CREATE TABLE identity_screened_identifiers (
    screen_id_pk           BIGSERIAL PRIMARY KEY,
    run_id                 BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    identity_namespace     TEXT NOT NULL,
    identity_value_hash    TEXT NOT NULL,
    identity_value_masked  TEXT,
    screen_id              TEXT NOT NULL,
    distinct_record_count  INTEGER NOT NULL,
    distinct_source_count  INTEGER NOT NULL
);

CREATE TABLE identity_review_queue (
    review_id              BIGSERIAL PRIMARY KEY,
    run_id                 BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    reason                 TEXT NOT NULL,
    candidate_cluster_key  TEXT,
    member_record_keys     JSONB,
    cut_edges              JSONB,
    min_edge_confidence    NUMERIC(4,3),
    status                 TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
    resolved_by            TEXT,
    resolved_at            TIMESTAMPTZ
);

CREATE TABLE identity_crosswalk (
    prior_canonical_customer_id  TEXT PRIMARY KEY,
    canonical_customer_id        TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    status                       TEXT NOT NULL CHECK (status IN ('current','merged','split')),
    first_seen_run_id            BIGINT,
    merged_in_run_id             BIGINT
);

-- ========================================================== SEGMENTATION

CREATE TABLE segments (
    segment_id       TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    description      TEXT,
    current_version  INTEGER NOT NULL DEFAULT 1,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_by       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE segment_versions (
    segment_id     TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
    version        INTEGER NOT NULL,
    rule_ast       JSONB NOT NULL CHECK (jsonb_typeof(rule_ast) = 'object'),
    thresholds     JSONB,
    null_handling  TEXT NOT NULL DEFAULT 'exclude' CHECK (null_handling IN ('exclude','include')),
    created_by     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (segment_id, version)
);

CREATE TABLE segment_members (
    segment_id             TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
    canonical_customer_id  TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    definition_version     INTEGER NOT NULL,
    entered_on             DATE NOT NULL,
    run_id                 BIGINT,
    PRIMARY KEY (segment_id, canonical_customer_id)
);
CREATE INDEX ix_segmem_customer ON segment_members (canonical_customer_id);
CREATE INDEX ix_segmem_segment ON segment_members (segment_id, entered_on DESC);

CREATE TABLE segment_membership_events (
    event_id                BIGSERIAL PRIMARY KEY,
    segment_id              TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
    canonical_customer_id   TEXT NOT NULL REFERENCES customers(canonical_customer_id) ON DELETE CASCADE,
    change_type             TEXT NOT NULL CHECK (change_type IN ('entered','exited')),
    reason                  TEXT NOT NULL CHECK (reason IN ('data_change','definition_change','identity_change')),
    definition_version      INTEGER NOT NULL,
    run_id                  BIGINT,
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_segevents_segment ON segment_membership_events (segment_id, occurred_at DESC);

CREATE TABLE segment_run_stats (
    run_stat_id         BIGSERIAL PRIMARY KEY,
    segment_id          TEXT NOT NULL REFERENCES segments(segment_id) ON DELETE CASCADE,
    run_id              BIGINT,
    definition_version  INTEGER NOT NULL,
    member_count        INTEGER NOT NULL,
    entered_count       INTEGER NOT NULL DEFAULT 0,
    exited_count        INTEGER NOT NULL DEFAULT 0,
    duration_ms         INTEGER,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================== SECURITY

CREATE TABLE roles (
    role_name    TEXT PRIMARY KEY,
    description  TEXT
);
INSERT INTO roles (role_name, description) VALUES
    ('viewer', 'Read-only access with PII masking'),
    ('analyst', 'CRM/marketing analyst; builds audiences, reads behaviour'),
    ('data_engineer', 'Owns pipeline runs, DQ remediation, identity review'),
    ('admin', 'Full access, user and role management');

CREATE TABLE users (
    user_id         BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_roles (
    user_id     BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_name   TEXT NOT NULL REFERENCES roles(role_name) ON DELETE CASCADE,
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, role_name)
);

CREATE TABLE refresh_tokens (
    jti          TEXT PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash   TEXT NOT NULL,
    family_id    TEXT NOT NULL,
    is_revoked   BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at   TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_tokens_user ON refresh_tokens (user_id);
CREATE INDEX ix_refresh_tokens_family ON refresh_tokens (family_id);

CREATE TABLE audit_logs (
    audit_log_id    BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    actor_email     TEXT,
    actor_role      TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    outcome         TEXT NOT NULL DEFAULT 'success',
    row_count       INTEGER,
    request_id      TEXT,
    ip_address      INET,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_actor_time ON audit_logs (user_id, occurred_at DESC);
CREATE INDEX ix_audit_resource ON audit_logs (resource_type, resource_id, occurred_at DESC);

CREATE TABLE jobs (
    job_id        TEXT PRIMARY KEY,
    job_type      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed')),
    params        JSONB,
    requested_by  BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    error_message TEXT
);
"""

DOWN_DDL = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"


def upgrade() -> None:
    op.execute(DDL)


def downgrade() -> None:
    op.execute(DOWN_DDL)
