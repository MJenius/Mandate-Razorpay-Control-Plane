"""Razorpay MCP Tool Catalog, Category Definitions, and Dynamic Mandate Filtering."""

from typing import Any

from packages.core.enums import OperationType
from packages.core.models import Agent, Mandate

# Comprehensive Tool Catalog covering Razorpay Model Context Protocol (MCP) server endpoints across all 8 functional domains:
# (Payments, Orders, Payment Links, Refunds, QR Codes, Settlements, Invoices, Payouts)
RAZORPAY_MCP_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # 1. Orders & Payments (Buyer / Purchasing tools)
    "payments_create_order": {
        "name": "payments_create_order",
        "description": "Creates an order for payment collection on Razorpay.",
        "category": "ORDERS",
        "operation_type": OperationType.CREATE_ORDER,
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Amount in smallest currency unit (paise for INR)",
                },
                "currency": {
                    "type": "string",
                    "description": "3-letter ISO currency code (e.g. INR)",
                },
                "receipt": {
                    "type": "string",
                    "description": "Unique receipt reference for the order",
                },
                "notes": {"type": "object", "description": "Key-value metadata dictionary"},
            },
            "required": ["amount", "currency"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_order": {
        "name": "payments_fetch_order",
        "description": "Fetches details of a specific Razorpay order.",
        "category": "ORDERS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Razorpay order ID (e.g. order_xxx)"},
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_all_orders": {
        "name": "payments_fetch_all_orders",
        "description": "Fetches a list of historical Razorpay orders.",
        "category": "ORDERS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of orders to retrieve"},
            },
            "additionalProperties": False,
        },
    },
    "payments_fetch_payment": {
        "name": "payments_fetch_payment",
        "description": "Fetches details of a specific Razorpay payment.",
        "category": "PAYMENTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "Razorpay payment ID (e.g. pay_xxx)",
                },
            },
            "required": ["payment_id"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_all_payments": {
        "name": "payments_fetch_all_payments",
        "description": "Fetches a list of all payments for the merchant account.",
        "category": "PAYMENTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of payments to fetch"},
            },
            "additionalProperties": False,
        },
    },
    "payments_capture_payment": {
        "name": "payments_capture_payment",
        "description": "Captures an authorized Razorpay payment.",
        "category": "PAYMENTS",
        "operation_type": OperationType.CAPTURE_PAYMENT,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string", "description": "Payment ID to capture"},
                "amount": {"type": "integer", "description": "Amount in paise"},
                "currency": {"type": "string", "description": "ISO currency code"},
            },
            "required": ["payment_id", "amount"],
            "additionalProperties": False,
        },
    },
    # 2. Payment Links & Invoicing (Merchant tools)
    "payments_create_payment_link": {
        "name": "payments_create_payment_link",
        "description": "Creates a shareable customer Payment Link for invoicing.",
        "category": "PAYMENT_LINKS",
        "operation_type": OperationType.CREATE_PAYMENT_LINK,
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount in paise"},
                "currency": {"type": "string", "description": "Currency code (e.g. INR)"},
                "description": {
                    "type": "string",
                    "description": "Payment link invoice description",
                },
                "customer_name": {"type": "string", "description": "Recipient name"},
                "customer_email": {"type": "string", "description": "Recipient email"},
                "customer_contact": {"type": "string", "description": "Recipient phone"},
                "notes": {"type": "object", "description": "Custom metadata"},
            },
            "required": ["amount", "currency", "description"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_payment_link": {
        "name": "payments_fetch_payment_link",
        "description": "Fetches status and details of a Payment Link.",
        "category": "PAYMENT_LINKS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_link_id": {"type": "string", "description": "Payment link ID"},
            },
            "required": ["payment_link_id"],
            "additionalProperties": False,
        },
    },
    "payments_cancel_payment_link": {
        "name": "payments_cancel_payment_link",
        "description": "Cancels an active Razorpay Payment Link.",
        "category": "PAYMENT_LINKS",
        "operation_type": OperationType.CANCEL_PAYMENT_LINK,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_link_id": {"type": "string", "description": "Payment link ID to cancel"},
            },
            "required": ["payment_link_id"],
            "additionalProperties": False,
        },
    },
    # 3. Customer Refunds (Support tools)
    "payments_create_refund": {
        "name": "payments_create_refund",
        "description": "Creates a refund for a previously captured payment.",
        "category": "REFUNDS",
        "operation_type": OperationType.CREATE_REFUND,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string", "description": "Payment ID to refund"},
                "amount": {
                    "type": "integer",
                    "description": "Refund amount in paise (optional for full refund)",
                },
                "notes": {"type": "object", "description": "Refund notes/reason"},
            },
            "required": ["payment_id"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_refund": {
        "name": "payments_fetch_refund",
        "description": "Fetches details of a specific refund transaction.",
        "category": "REFUNDS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "refund_id": {"type": "string", "description": "Refund ID"},
            },
            "required": ["refund_id"],
            "additionalProperties": False,
        },
    },
    "payments_fetch_all_refunds": {
        "name": "payments_fetch_all_refunds",
        "description": "Fetches a list of all refunds processed for the account.",
        "category": "REFUNDS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of refunds to retrieve"},
            },
            "additionalProperties": False,
        },
    },
    # 4. QR Codes & Instant Collection
    "qr_codes_create": {
        "name": "qr_codes_create",
        "description": "Creates a dynamic BharatQR / UPI QR code for payment collection.",
        "category": "QR_CODES",
        "operation_type": OperationType.CREATE_ORDER,
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "upi_qr"},
                "name": {"type": "string", "description": "Store or desk reference name"},
                "usage": {"type": "string", "description": "single_use or multiple_use"},
                "fixed_amount": {"type": "boolean", "description": "Whether amount is fixed"},
                "payment_amount": {"type": "integer", "description": "Amount in paise"},
            },
            "required": ["type", "name", "usage"],
            "additionalProperties": False,
        },
    },
    "qr_codes_fetch_by_id": {
        "name": "qr_codes_fetch_by_id",
        "description": "Fetches status of a generated QR code.",
        "category": "QR_CODES",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "qr_id": {"type": "string", "description": "QR Code ID"},
            },
            "required": ["qr_id"],
            "additionalProperties": False,
        },
    },
    "qr_codes_close": {
        "name": "qr_codes_close",
        "description": "Closes an active QR code.",
        "category": "QR_CODES",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "qr_id": {"type": "string", "description": "QR Code ID to close"},
            },
            "required": ["qr_id"],
            "additionalProperties": False,
        },
    },
    # 5. Merchant Settlements & Bank Reconciliation (Finance tools)
    "settlements_fetch_all": {
        "name": "settlements_fetch_all",
        "description": "Fetches all bank settlement transfers for the merchant account.",
        "category": "SETTLEMENTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of settlements"},
            },
            "additionalProperties": False,
        },
    },
    "settlements_fetch_by_id": {
        "name": "settlements_fetch_by_id",
        "description": "Fetches details of a specific bank settlement transfer.",
        "category": "SETTLEMENTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "settlement_id": {"type": "string", "description": "Settlement ID"},
            },
            "required": ["settlement_id"],
            "additionalProperties": False,
        },
    },
    "settlements_fetch_combined_report": {
        "name": "settlements_fetch_combined_report",
        "description": "Fetches a consolidated settlement report for accounting reconciliation.",
        "category": "SETTLEMENTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Year of report"},
                "month": {"type": "integer", "description": "Month of report"},
            },
            "additionalProperties": False,
        },
    },
    # 6. Invoices & Billing
    "invoices_create": {
        "name": "invoices_create",
        "description": "Issues a formal GST-compliant invoice for customer billing.",
        "category": "INVOICES",
        "operation_type": OperationType.CREATE_PAYMENT_LINK,
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "invoice"},
                "description": {"type": "string", "description": "Billing line item"},
                "amount": {"type": "integer", "description": "Amount in paise"},
                "customer": {"type": "object", "description": "Customer contact info"},
            },
            "required": ["type", "description", "amount"],
            "additionalProperties": False,
        },
    },
    "invoices_fetch_by_id": {
        "name": "invoices_fetch_by_id",
        "description": "Fetches details of an issued invoice.",
        "category": "INVOICES",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "Invoice ID"},
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    },
    "invoices_cancel": {
        "name": "invoices_cancel",
        "description": "Cancels an issued unpaid invoice.",
        "category": "INVOICES",
        "operation_type": OperationType.CANCEL_PAYMENT_LINK,
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "Invoice ID to cancel"},
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    },
    # 7. Customers & Tokenization
    "customers_create": {
        "name": "customers_create",
        "description": "Creates a customer entity on Razorpay for recurring billing.",
        "category": "CUSTOMERS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name"},
                "email": {"type": "string", "description": "Customer email"},
                "contact": {"type": "string", "description": "Customer phone"},
            },
            "required": ["name", "email"],
            "additionalProperties": False,
        },
    },
    "customers_fetch_by_id": {
        "name": "customers_fetch_by_id",
        "description": "Fetches customer details.",
        "category": "CUSTOMERS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    },
    # 8. Privileged Banking Payouts (RazorpayX Restricted Tools)
    "payouts_create": {
        "name": "payouts_create",
        "description": "Dispatches an external bank payout from merchant account.",
        "category": "PAYOUTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_number": {"type": "string", "description": "Destination bank account"},
                "fund_account_id": {"type": "string", "description": "RazorpayX fund account"},
                "amount": {"type": "integer", "description": "Amount in paise"},
                "currency": {"type": "string", "description": "INR"},
                "mode": {"type": "string", "description": "IMPS, NEFT, RTGS"},
                "purpose": {"type": "string", "description": "Payout purpose"},
            },
            "required": ["account_number", "amount", "currency", "mode", "purpose"],
            "additionalProperties": False,
        },
    },
    "payouts_fetch_by_id": {
        "name": "payouts_fetch_by_id",
        "description": "Fetches status of an external bank payout transfer.",
        "category": "PAYOUTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payout_id": {"type": "string", "description": "Payout ID"},
            },
            "required": ["payout_id"],
            "additionalProperties": False,
        },
    },
    "payouts_cancel": {
        "name": "payouts_cancel",
        "description": "Cancels a queued external bank payout.",
        "category": "PAYOUTS",
        "operation_type": None,
        "inputSchema": {
            "type": "object",
            "properties": {
                "payout_id": {"type": "string", "description": "Payout ID to cancel"},
            },
            "required": ["payout_id"],
            "additionalProperties": False,
        },
    },
}

TOTAL_REGISTRY_TOOL_COUNT = len(RAZORPAY_MCP_TOOL_REGISTRY)


def get_filtered_mcp_tools(agent: Agent, mandate: Mandate) -> list[dict[str, Any]]:
    """
    Dynamic MCP Tool Filtering:
    Filters the registered Razorpay MCP tool surface down to the exact subset authorized
    by the calling AI Agent's active financial mandate.
    """
    filtered_tools: list[dict[str, Any]] = []

    for _tool_name, tool_def in RAZORPAY_MCP_TOOL_REGISTRY.items():
        op_type = tool_def.get("operation_type")

        # 1. Read-only informative tools:
        if op_type is None:
            # Sensitive categories (e.g. PAYOUTS, SETTLEMENTS) require explicit permission in mandate
            if tool_def["category"] == "PAYOUTS":
                if "PAYOUTS" in mandate.allowed_operations:
                    filtered_tools.append(tool_def)
            elif tool_def["category"] == "SETTLEMENTS":
                if "SETTLEMENTS" in mandate.allowed_operations or agent.agent_type in [
                    "FINANCE",
                    "ADMIN",
                ]:
                    filtered_tools.append(tool_def)
            else:
                filtered_tools.append(tool_def)
            continue

        # 2. Mutating financial tools:
        op_str = op_type.value if hasattr(op_type, "value") else str(op_type)
        if op_str in mandate.allowed_operations:
            filtered_tools.append(tool_def)

    return filtered_tools
