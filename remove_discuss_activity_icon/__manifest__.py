# -*- coding: utf-8 -*-
{
    'name': "Remove discuss/activity icon",
    'summary': "Remove top right discuss and activity icons",
    'description': """
        Remove top right discuss and activity icons.
    """,
    'images': ['static/description/banner.png'],  # 560x280 px
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'mail'],
    'assets': {
        'web.assets_backend': [
            'remove_discuss_activity_icon/static/src/*.xml',
        ]
    },
    'installable': True,
    'application': False,
}
