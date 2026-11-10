# -*- coding: utf-8 -*-
{
    'name': 'Product Availability Notification',
    'summary': 'Activate or deactivate the product availability notification.',
    'description': 'Activate or deactivate the product availability notification.',
    'category': 'Website/Website',
    'version': '0.1.0',
    'license': 'AGPL-3',
    'author': 'HVG Solutions',
    'website': 'https://hvg-solutions.com',
    'price': 0,
    'currency': 'EUR',
    'depends': ['website_sale_stock'],
    'data': [
        'views/product_page_templates.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'website_sale_stock_notification/static/tests/tours/*.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
