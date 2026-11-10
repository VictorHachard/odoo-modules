# -*- coding: utf-8 -*-
{
    'name': 'Enhanced Security Custom Search',
    'summary': 'Hides the ad-hoc search controls from users outside a dedicated group.',
    'description': """
Enhanced Security Custom Search
===============================

Adds a group, "Enable Custom Search", and hides the ad-hoc search controls from
every user who is not in it: the "Custom Filter..." and "Custom Date..." entries
of the search panel (and the "Custom Filter..." of the search autocomplete), the
"Add Custom Group" entry of the search panel and of the pivot header, the pencil
that opens the domain editor on a search facet, and "Save current search" in the
Favorites column.

Every internal user holds the group by default (existing users at install, new
users through the default user template); remove it from the users who should
only use the predefined filters.

Scope, stated plainly: this is a user interface simplification, not an access
control over data. The one server-side rule it adds is on ir.filters
create / write / unlink, so saving, renaming and deleting a favourite really is
refused for a user outside the group, and a filter shared with other users can
only be changed or deleted by its author or an administrator. Applying a domain
or a group-by is not gated, and cannot be: the web client sends the domain and
the groupby list straight to the read RPC on every screen it opens, and the
server has no way to tell a domain the search view produced from a domain a
user typed. Record rules and model access rights remain the only fence around
the data itself.
    """,
    'images': ['static/description/banner.png'],  # 560x280 px
    'category': 'Technical',
    'version': '1.0.0',
    'author': 'HVG Solutions',
    'website': 'https://hvg-solutions.com',
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
            # PivotRenderer only exists in the lazy bundle, so a patch on it
            # cannot resolve its import from assets_backend.
            ('remove', 'enhanced_security_search/static/src/pivot_renderer/**'),
        ],
        'web.assets_backend_lazy': [
            'enhanced_security_search/static/src/pivot_renderer/**',
        ],
        'web.assets_unit_tests': [
            'enhanced_security_search/static/tests/**/*.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_init',
}
