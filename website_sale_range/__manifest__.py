# -*- coding: utf-8 -*-
{
    "name": "Website Sale Range Filter",
    "summary": """Add a range filter to the shop page""",
    'description': """Add a range filter to the shop page like the price filter""",
    'images': ['static/description/banner.png'],  # 560x280 px
    "category": "Website",
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    "depends": [
        'website_sale',
    ],
    "data": [
        'views/product_attribute.xml',
        'views/templates.xml',
    ],
    "assets": {
        'web.assets_frontend': [
            'website_sale_range/static/src/js/*.js',
        ],
    },
    "application": True,
    "installable": True,
}
