# -*- coding: utf-8 -*-
{
    'name': "Contacts Icon Plus",
    'summary': "Enhances contact management with custom icons and types.",
    'description': "This module adds custom icons and types to contacts in Odoo, making it easier to distinguish between individuals, employees, companies, and contacts.",
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'contacts'],
    'data': [
        'security/res_groups.xml',

        'views/res_partner_inherit.xml',
        'views/res_users_inherit.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contacts_icon_plus/static/src/*.xml',
            'contacts_icon_plus/static/src/*.scss',
            'contacts_icon_plus/static/src/*.js',
        ]
    },
    'installable': True,
    'application': False,
}
