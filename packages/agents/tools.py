"""Agent Tool Definitions, Catalog dataset, and Mandate tool call conversions."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Synthetic Product Catalog for Shopping Agent
PRODUCTS_CATALOG: Dict[str, Dict[str, Any]] = {
    "prod_kb_01": {
        "id": "prod_kb_01",
        "name": "Keychron K2 Mechanical Keyboard",
        "category": "Electronics",
        "price_paise": 650000, # 6,500 INR
        "description": "Wireless Mechanical Keyboard with Gateron switches",
        "stock": 15,
    },
    "prod_mouse_01": {
        "id": "prod_mouse_01",
        "name": "Logitech MX Master 3S Mouse",
        "category": "Electronics",
        "price_paise": 899900, # 8,999 INR
        "description": "Performance Wireless Mouse with ergonomic grip",
        "stock": 8,
    },
    "prod_desk_mat_01": {
        "id": "prod_desk_mat_01",
        "name": "Ergonomic Wool Felt Desk Mat",
        "category": "Accessories",
        "price_paise": 150000, # 1,500 INR
        "description": "Premium non-slip desk protector",
        "stock": 50,
    },
    "prod_monitor_high_end": {
        "id": "prod_monitor_high_end",
        "name": "Dell UltraSharp 32-inch 4K Monitor",
        "category": "Electronics",
        "price_paise": 7500000, # 75,000 INR (Useful for testing per-op limit rejection)
        "description": "Professional color-accurate 4K USB-C monitor",
        "stock": 3,
    },
    "prod_enterprise_server": {
        "id": "prod_enterprise_server",
        "name": "Rackmount GPU AI Workstation",
        "category": "Enterprise",
        "price_paise": 45000000, # 4,50,000 INR (Useful for testing aggregate limit rejection)
        "description": "Dedicated on-prem inference rack",
        "stock": 1,
    },
}

# OpenAI Structured Tool Definitions Schema
SHOPPING_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browse_catalog",
            "description": "List available products in the catalog with prices and stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'Electronics', 'Accessories')",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_purchase_order",
            "description": "Creates a financial order to purchase a catalog item through Mandate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The exact product SKU ID (e.g. 'prod_kb_01')",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of items to purchase (must be >= 1)",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Name of the customer purchasing the item",
                    },
                },
                "required": ["product_id", "quantity", "customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_payment_link_for_customer",
            "description": "Creates a shareable Razorpay payment link for a customer invoice or purchase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount_in_rupees": {
                        "type": "number",
                        "description": "Total amount in INR (e.g. 1500 for Rs. 1500)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the payment link purpose",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Customer recipient name",
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "Customer email address",
                    },
                },
                "required": ["amount_in_rupees", "description", "customer_email"],
            },
        },
    },
]

SUPPORT_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_transaction",
            "description": "Inspects details and gateway status of an operation or transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_id": {
                        "type": "string",
                        "description": "The unique operation ID to look up (e.g. 'op_xxx')",
                    },
                },
                "required": ["operation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_customer_refund",
            "description": "Issues a bounded refund for a customer payment through Mandate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "payment_id": {
                        "type": "string",
                        "description": "Razorpay payment ID to refund (e.g. 'pay_xxx')",
                    },
                    "amount_in_rupees": {
                        "type": "number",
                        "description": "Amount to refund in INR. If omitted, full refund.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Documented reason for customer refund",
                    },
                },
                "required": ["payment_id", "reason"],
            },
        },
    },
]


def execute_local_catalog_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes non-financial informative tool (e.g. browsing product catalog)."""
    if tool_name == "browse_catalog":
        category = arguments.get("category")
        results = []
        for p in PRODUCTS_CATALOG.values():
            if not category or p["category"].lower() == category.lower():
                results.append({
                    "product_id": p["id"],
                    "name": p["name"],
                    "category": p["category"],
                    "price_inr": f"Rs. {p['price_paise'] / 100:,.2f}",
                    "price_paise": p["price_paise"],
                    "in_stock": p["stock"] > 0,
                })
        return {"catalog_items": results}
    return {"error": f"Unknown local tool '{tool_name}'"}
