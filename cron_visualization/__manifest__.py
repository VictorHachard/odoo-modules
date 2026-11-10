# -*- coding: utf-8 -*-
{
    'name': 'Enhanced Cron Visualization',
    'summary': 'Real-time kanban dashboard to monitor the cron jobs running in your Odoo instance.',
    'description': """
Enhanced Cron Visualization
===========================

Visualize and monitor the scheduled actions (cron jobs) running in your Odoo
instance from a live kanban dashboard.

* Real-time updates pushed through the bus (no polling, no periodic refresh),
  delivered to Settings users only.
* Per-cron run history with state, duration, type (manual / automatic),
  operator and error message.
* Running indicator, estimated progress bar and next-execution countdown.
* List, pivot, graph and calendar analysis of the run history.
* Runs left behind by a killed worker are detected and flagged as interrupted.
* Automatic cleanup of the history (90 days by default, configurable through
  the ``cron_visualization.history_retention_days`` system parameter).
    """,
    'images': ['static/description/banner.gif'],  # 560x280 px
    'category': 'Technical',
    'version': '1.1.0',
    'author': 'HVG Solutions',
    'website': 'https://hvg-solutions.com',
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'bus'],
    'data': [
        'security/ir.model.access.csv',

        'views/cv_ir_cron_history.xml',
        'views/ir_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cron_visualization/static/src/*/*.scss',
            'cron_visualization/static/src/*/*.xml',
            'cron_visualization/static/src/*/*.js',
            'cron_visualization/static/src/backend_style.scss',
        ],
        'web.assets_unit_tests': [
            'cron_visualization/static/tests/**/*.js',
        ],
    },
    'installable': True,
    'application': False,
    'uninstall_hook': '_uninstall_hook',
}
