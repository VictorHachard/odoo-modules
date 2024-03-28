# -*- coding: utf-8 -*-
{
    'name': "Border and Center - Tree View",
    'summary': "Add border and center text tree view",
    'description': "This module add border and center text in tree view",
    'images': ['static/description/banner.png'],  # 560x280 px
    'category': 'Technical',
    'version': '0.0.2',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'tree_style_border_center/static/src/*.scss',
        ]
    },
    'installable': True,
    'application': False,
}
