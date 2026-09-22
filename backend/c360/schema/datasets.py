"""Concrete dataset contracts for D-01..D-09 (§4)."""
from __future__ import annotations

from .contracts import ColumnContract as C
from .contracts import DatasetContract
from .contracts import Sensitivity as S
from .contracts import SemanticType as T

ISO_TS = ("yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd'T'HH:mm:ssXXX")
MIXED_TS = ISO_TS + ("dd-MM-yyyy HH:mm", "dd/MM/yyyy HH:mm", "yyyy-MM-dd HH:mm:ss")

CUSTOMERS_CRM = DatasetContract(
    dataset_id="D-01", name="customers_crm", version=1, source_system="crm",
    primary_key=("crm_customer_id",),
    columns=(
        C("crm_customer_id", "string", True, T.IDENTIFIER, S.INTERNAL, identity_namespace="crm_id"),
        C("first_name", "string", True, T.NAME, S.PII),
        C("last_name", "string", True, T.NAME, S.PII),
        C("email", "string", False, T.IDENTIFIER, S.PII, identity_namespace="email"),
        C("phone", "string", False, T.IDENTIFIER, S.PII, identity_namespace="phone"),
        C("date_of_birth", "date", False, T.DEMOGRAPHIC, S.SENSITIVE_PII),
        C("gender", "string", False, T.DEMOGRAPHIC, S.SENSITIVE_PII),
        C("city", "string", False, T.ADDRESS, S.PII),
        C("state", "string", False, T.ADDRESS, S.PII),
        C("country", "string", False, T.ADDRESS, S.INTERNAL),
        C("postal_code", "string", False, T.ADDRESS, S.PII),
        C("account_status", "string", True, T.STATUS, S.INTERNAL,
          enum_values=("active", "inactive", "churned")),
        C("signup_channel", "string", False, T.ATTRIBUTE, S.INTERNAL,
          enum_values=("web", "store", "partner", "import")),
        C("created_at", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("updated_at", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
    ),
)

LOYALTY_MEMBERS = DatasetContract(
    dataset_id="D-02", name="loyalty_members", version=1, source_system="loyalty",
    primary_key=("loyalty_id",),
    columns=(
        C("loyalty_id", "string", True, T.IDENTIFIER, S.INTERNAL, identity_namespace="loyalty_id"),
        C("member_name", "string", True, T.NAME, S.PII),
        C("mobile", "string", True, T.IDENTIFIER, S.PII, identity_namespace="phone"),
        C("email_address", "string", False, T.IDENTIFIER, S.PII, identity_namespace="email"),
        C("tier", "string", True, T.ATTRIBUTE, S.INTERNAL, enum_values=("bronze", "silver", "gold", "platinum")),
        C("points_balance", "integer", True, T.ATTRIBUTE, S.INTERNAL),
        C("enrolled_on", "date", True, T.AUDIT, S.INTERNAL),
        C("home_store", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("city", "string", False, T.ADDRESS, S.PII),
        C("country_code", "string", False, T.ADDRESS, S.INTERNAL),
        C("last_updated", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=("dd/MM/yyyy HH:mm",)),
    ),
)

APP_USERS = DatasetContract(
    dataset_id="D-03", name="app_users", version=1, source_system="app",
    primary_key=("app_user_id",),
    columns=(
        C("app_user_id", "string", True, T.IDENTIFIER, S.INTERNAL, identity_namespace="app_user_id"),
        C("email", "string", True, T.IDENTIFIER, S.PII, identity_namespace="email"),
        C("display_name", "string", False, T.NAME, S.PII),
        C("phone_verified", "boolean", False, T.ATTRIBUTE, S.INTERNAL,
          bool_true_values=("y", "yes", "1", "true"), bool_false_values=("n", "no", "0", "false", "")),
        C("phone", "string", False, T.IDENTIFIER, S.PII, identity_namespace="phone"),
        C("locale", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("signup_ts", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("marketing_opt_in", "boolean", False, T.CONSENT, S.SENSITIVE_PII,
          bool_true_values=("true", "1"), bool_false_values=("false", "0", "")),
        C("last_login_ts", "timestamp", False, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("device_cookies", "array<string>", False, T.IDENTIFIER, S.INTERNAL),
    ),
)

PRODUCTS = DatasetContract(
    dataset_id="D-04", name="products", version=1, source_system="catalogue",
    primary_key=("product_id",),
    columns=(
        C("product_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("sku", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("product_name", "string", True, T.ATTRIBUTE, S.INTERNAL),
        C("category_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("category_name", "string", True, T.ATTRIBUTE, S.INTERNAL),
        C("brand", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("unit_price", "decimal", True, T.MONEY, S.INTERNAL),
        C("currency", "string", True, T.MONEY, S.INTERNAL),
        C("is_active", "boolean", True, T.STATUS, S.INTERNAL),
        C("stock_qty", "integer", False, T.ATTRIBUTE, S.INTERNAL),
        C("launched_on", "date", False, T.AUDIT, S.INTERNAL),
    ),
)

ORDERS = DatasetContract(
    dataset_id="D-05", name="orders", version=1, source_system="orders",
    primary_key=("order_id",),
    columns=(
        C("order_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("customer_ref", "string", False, T.IDENTIFIER, S.PII),
        C("customer_ref_type", "string", False, T.ATTRIBUTE, S.INTERNAL,
          enum_values=("crm_id", "app_user_id", "email")),
        C("order_ts", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=MIXED_TS),
        C("order_status", "string", True, T.STATUS, S.INTERNAL,
          enum_values=("placed", "paid", "shipped", "delivered", "cancelled", "refunded")),
        C("order_type", "string", True, T.ATTRIBUTE, S.INTERNAL, enum_values=("sale", "refund")),
        C("currency", "string", True, T.MONEY, S.INTERNAL),
        C("gross_amount", "decimal", True, T.MONEY, S.INTERNAL),
        C("discount_amount", "decimal", False, T.MONEY, S.INTERNAL),
        C("shipping_amount", "decimal", False, T.MONEY, S.INTERNAL),
        C("tax_amount", "decimal", False, T.MONEY, S.INTERNAL),
        C("payment_method", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("channel", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("ship_country", "string", False, T.ADDRESS, S.INTERNAL),
        C("updated_at", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
    ),
)

ORDER_ITEMS = DatasetContract(
    dataset_id="D-06", name="order_items", version=1, source_system="orders",
    primary_key=("order_id", "line_number"),
    columns=(
        C("order_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("line_number", "integer", True, T.IDENTIFIER, S.INTERNAL),
        C("product_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("quantity", "integer", True, T.ATTRIBUTE, S.INTERNAL),
        C("unit_price", "decimal", True, T.MONEY, S.INTERNAL),
        C("line_discount", "decimal", False, T.MONEY, S.INTERNAL),
    ),
)

WEB_EVENTS = DatasetContract(
    dataset_id="D-07", name="web_events", version=1, source_system="clickstream",
    primary_key=("event_id",),
    columns=(
        C("event_id", "string", False, T.IDENTIFIER, S.INTERNAL),
        C("event_type", "string", True, T.ATTRIBUTE, S.INTERNAL),
        C("event_ts", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("app_user_id", "string", False, T.IDENTIFIER, S.INTERNAL, identity_namespace="app_user_id"),
        C("device_cookie", "string", True, T.IDENTIFIER, S.INTERNAL, identity_namespace="device_cookie"),
        C("session_hint", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("page_url", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("referrer", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("product_id", "string", False, T.IDENTIFIER, S.INTERNAL),
        C("search_term", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("cart_value", "decimal", False, T.MONEY, S.INTERNAL),
        C("utm_source", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("utm_medium", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("utm_campaign", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("device_type", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("country", "string", False, T.ADDRESS, S.INTERNAL),
        C("user_agent", "string", False, T.ATTRIBUTE, S.INTERNAL),
    ),
)

SUPPORT_TICKETS = DatasetContract(
    dataset_id="D-08", name="support_tickets", version=1, source_system="support",
    primary_key=("ticket_id",),
    columns=(
        C("ticket_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("requester_email", "string", True, T.IDENTIFIER, S.PII, identity_namespace="email"),
        C("subject", "string", True, T.ATTRIBUTE, S.INTERNAL),
        C("category", "string", True, T.ATTRIBUTE, S.INTERNAL,
          enum_values=("delivery", "refund", "product_quality", "payment", "account", "other")),
        C("priority", "string", True, T.ATTRIBUTE, S.INTERNAL, enum_values=("low", "medium", "high", "urgent")),
        C("status", "string", True, T.STATUS, S.INTERNAL, enum_values=("open", "pending", "resolved", "closed")),
        C("created_at", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("first_response_at", "timestamp", False, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("resolved_at", "timestamp", False, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("satisfaction_score", "integer", False, T.ATTRIBUTE, S.INTERNAL),
        C("order_id", "string", False, T.IDENTIFIER, S.INTERNAL),
    ),
)

MARKETING_EVENTS = DatasetContract(
    dataset_id="D-09", name="marketing_events", version=1, source_system="marketing",
    primary_key=("campaign_id", "recipient_email", "event_type", "event_ts"),
    columns=(
        C("campaign_id", "string", True, T.IDENTIFIER, S.INTERNAL),
        C("campaign_name", "string", True, T.ATTRIBUTE, S.INTERNAL),
        C("channel", "string", True, T.ATTRIBUTE, S.INTERNAL, enum_values=("email", "push", "sms")),
        C("recipient_email", "string", True, T.IDENTIFIER, S.PII, identity_namespace="email"),
        C("event_type", "string", True, T.ATTRIBUTE, S.INTERNAL,
          enum_values=("sent", "delivered", "open", "click", "bounce", "unsubscribe")),
        C("event_ts", "timestamp", True, T.AUDIT, S.INTERNAL, timestamp_patterns=ISO_TS),
        C("link_url", "string", False, T.ATTRIBUTE, S.INTERNAL),
        C("product_id", "string", False, T.IDENTIFIER, S.INTERNAL),
    ),
)

ALL_CONTRACTS: dict[str, DatasetContract] = {
    c.name: c for c in [
        CUSTOMERS_CRM, LOYALTY_MEMBERS, APP_USERS, PRODUCTS, ORDERS,
        ORDER_ITEMS, WEB_EVENTS, SUPPORT_TICKETS, MARKETING_EVENTS,
    ]
}
