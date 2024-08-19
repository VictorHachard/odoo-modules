# -*- coding: utf-8 -*-
{
    'name': "Export data to PDF",
    'summary': """Add PDF export format to the export menu""",
    'description': """Add PDF export format to the export menu""",
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base'],
    'data': [
        'report/export_pdf.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}