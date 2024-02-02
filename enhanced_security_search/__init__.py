# -*- coding: utf-8 -*-

def _post_init(env):
    internal_users = env['res.users'].sudo().search([('share', '=', False)])
    group_custom_search = env.ref('enhanced_security_search.group_custom_search')
    group_custom_favorite_share = env.ref('enhanced_security_search.group_custom_favorite_share')
    for user in internal_users:
        user.groups_id |= group_custom_search | group_custom_favorite_share
