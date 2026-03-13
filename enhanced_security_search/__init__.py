# -*- coding: utf-8 -*-

def _post_init(env):
    internal_users = env['res.users'].sudo().search([('share', '=', False)])
    group_custom_search = env.ref('enhanced_security_search.group_custom_search')
    for user in internal_users:
        user.group_ids |= group_custom_search
