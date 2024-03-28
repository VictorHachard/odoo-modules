# -*- coding: utf-8 -*-
{
    'name': "Account Siret on Invoice",
    'summary': "Add Siret number on invoice report",
    'description': """
        Add Siret number on invoice report
    """,
    'category': 'Accounting/Accounting',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'account', 'l10n_fr'],
    'data': [
        'views/report_invoice.xml',
    ],
    'installable': True,
    'application': False,
}
