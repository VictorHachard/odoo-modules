# -*- coding: utf-8 -*-
{
    "name": "Product Availability Notification",
    "summary": "Activate or deactivate the product availability notification.",
    "description": "Activate or deactivate the product availability notification.",
    "category": 'Website/Website',
    "version": "0.0.1",
    "license": "AGPL-3",
    "author": "Victor",
    "price": 0,
    "currency": 'EUR',
    "depends": ["website_sale_stock"],
    "data": [
        "views/product_template.xml",
        "views/res_config_settings.xml",
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_stock_notification/static/src/js/*',
        ],
    },
    "installable": True,
    'application': False,
    "auto_install": False,
}
