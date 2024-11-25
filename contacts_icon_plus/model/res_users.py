# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    partner_icon_type_detailed = fields.Boolean(string='Show Contact Icons', default=False,
                                                help='Enable this option to display detailed icons for contacts')

    @api.model_create_multi
    def create(self, vals_list):
        group_id = self.env.ref('contacts_icon_plus.group_partner_icon_type_detailed').id
        for vals in vals_list:
            if vals.get('partner_icon_type_detailed', False):
                vals['groups_id'].append((4, group_id))
        return super().create(vals_list)

    def write(self, vals):
        group_id = self.env.ref('contacts_icon_plus.group_partner_icon_type_detailed').id
        if 'partner_icon_type_detailed' in vals:
            if vals['partner_icon_type_detailed']:
                vals.setdefault('groups_id', []).append((4, group_id))
            else:
                vals.setdefault('groups_id', []).append((3, group_id))
        return super().write(vals)
