# -*- coding: utf-8 -*-
{
    'name': 'Batch Record Import/Export with Template',
    'summary': 'Streamline record exports across multiple models using templates and filters.',
    'description':
        """
This module simplifies the process of exporting multiple records from various models by offering a versatile template-based approach.
Users can create export templates and apply filters based on specific domains, making record management more efficient and tailored to your needs.
""",
    'category': 'Technical',
    'version': '1.5.0',
    'author': 'HVG Solutions',
    'website': 'https://hvg-solutions.com',
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'web', 'base_import'],
    'data': [
        'security/ir.access.csv',

        'data/ier_exports.xml',

        'wizard/ier_export_records.xml',
        'wizard/ier_import_records.xml',

        'views/ier_template.xml',
        'views/ier_template_action_history.xml',

        'views/ier_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'import_export_records/static/src/backend.scss',

            'import_export_records/static/src/widget/*.js',
            'import_export_records/static/src/widget/*.xml',
            'import_export_records/static/src/widget/*.scss',

            'import_export_records/static/src/list_btn/*.js',
            'import_export_records/static/src/list_btn/*.xml',
        ],
        'web.assets_unit_tests': [
            'import_export_records/static/tests/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
