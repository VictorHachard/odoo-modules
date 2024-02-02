# -*- coding: utf-8 -*-
{
    'name': "Web Widget Image Field",
    'summary': "Add a widget on relational fields to display an image",
    'description': """
    Add a widget on relational fields to display an image like a avatar on users.
    """,
    'images': ['static/description/banner.png'],  # 560x280 px
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'web'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'web_widget_image_field/static/src/many2one_image_field/*.js',
            'web_widget_image_field/static/src/many2one_image_field/*.xml',
        ],
    },
    'installable': True,
    'application': False,
}
