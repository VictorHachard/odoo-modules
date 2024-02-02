# -*- coding: utf-8 -*-
{
    'name': "Enhanced Security Custom Search",
    'summary': "Enhances Odoo's custom search with customizable security options.",
    'description': """This module allows to manage access to custom filters, custom group by, and shared favorites in Odoo through user group assignments.""",
    'images': ['static/description/banner.png'],  # 560x280 px
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'web'],
    'data': [
        'security/res_groups.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'enhanced_security_search/static/src/*/*.xml',
            'enhanced_security_search/static/src/*/*.js',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': '_post_init',
}
