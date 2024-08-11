# -*- coding: utf-8 -*-
{
    "name": "Mermaid Widget",
    "summary": "Add Mermaid Diagrams to Odoo",
    "description": "Add the Mermaid.js library to Odoo and create a widget to display Mermaid diagrams in Odoo views.",
    "images": ['static/description/banner.png'],  # 560x280 px
    "category": "Technical",
    "version": "0.0.4",
    "author": "Victor",
    "license": 'LGPL-3',
    "price": 0,
    "currency": 'EUR',
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_widget_mermaid_field/static/src/js/web_widget_mermaid.js",
            "web_widget_mermaid_field/static/src/xml/mermaid_field.xml",
        ],
    },
    "installable": True,
    'application': False,
}