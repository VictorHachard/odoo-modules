# -*- coding: utf-8 -*-

from odoo import Command

from . import models


def _post_init(env):
    """Grant the group to the internal users that already exist.

    Future internal users get it from `base.default_user_group`, which
    `security/res_groups.xml` links the group into. This hook is the other half
    of that one policy: without it the population would be split between users
    created before the install and users created after.

    One write, not one per user: writing `group_ids` clears the group ormcache
    and recomputes the implied-group closure every time.
    """
    # Archived users included: reactivating one must not make them the only
    # internal user without the group.
    internal_users = env['res.users'].sudo().with_context(active_test=False).search([
        ('share', '=', False),
    ])
    if not internal_users:
        return
    group_custom_search = env.ref('enhanced_security_search.group_custom_search')
    group_custom_search.sudo().write({
        'user_ids': [Command.link(user_id) for user_id in internal_users.ids],
    })
