# -*- coding: utf-8 -*-
{
    'name': "Recompute Computed Field",
    'summary': """Recompute Computed Field""",
    'description': """Add a button to recompute computed fields in Odoo fields view.""",
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base'],
    'data': [
        'views/ir_model_field.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
