# -*- coding: utf-8 -*-
{
    "name": "Purchase Stock Flowchart",
    "summary": "This module adds a flowchart to the Purchase Order to show the stock flow.",
    "description": "This module enhances the Purchase Order by adding a flowchart that visually represents the stock flow, providing a clearer understanding of inventory movements associated with each order.",
    'images': ['static/description/banner.png'],  # 560x280 px
    "category": 'Inventory/Purchase',
    "version": "0.0.3",
    "license": "AGPL-3",
    "author": "Victor",
    "price": 0,
    "currency": 'EUR',
    "depends": ["purchase_stock", "purchase", "stock", 'stock_flowchart', 'web_widget_mermaid_field'],
    "data": [
        "views/purchase_order.xml",
    ],
    "installable": True,
    'application': True,
}
