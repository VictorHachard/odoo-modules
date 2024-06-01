# -*- coding: utf-8 -*-
{
    "name": "Sale Stock Flowchart",
    "summary": "This module adds a flowchart to the Sale Order to show the stock flow.",
    "description": "This module enhances the Sale Order by adding a flowchart that visually represents the stock flow, providing a clearer understanding of inventory movements associated with each order.",
    'images': ['static/description/banner.png'],  # 560x280 px
    "category": "Sales/Sales",
    "version": "0.0.1",
    "license": "AGPL-3",
    "author": "Victor",
    "price": 0,
    "currency": 'EUR',
    "depends": ["sale_management", "stock", 'stock_flowchart', 'web_widget_mermaid_field'],
    "data": [
        "views/sale_order.xml",
    ],
    "installable": True,
    'application': True,
}
