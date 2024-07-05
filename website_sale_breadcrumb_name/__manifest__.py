# -*- coding: utf-8 -*-
{
    "name": "Website Breadcumb Custom",
    "summary": "Update the breadcrumb name of the website product page",
    "description": "Update the breadcrumb name of the website product page",
    'images': ['static/description/banner.jpg'],  # 560x280 px
    "category": 'Hidden',
    "version": "0.0.1",
    "license": "AGPL-3",
    "author": "Victor",
    "price": 0,
    "currency": 'EUR',
    "depends": ["website_sale"],
    "data": [
        "views/res_config_settings.xml",
        "views/website_template.xml",
    ],
    "installable": True,
    'application': False,
    "auto_install": False,
}
