# -*- coding: utf-8 -*-

from odoo import Command, api, fields, models

DETAILED_ICON_GROUP = 'contacts_icon_plus.group_partner_icon_type_detailed'


class ResUsers(models.Model):
    _inherit = 'res.users'

    partner_icon_type_detailed = fields.Boolean(
        string='Show Contact Icons',
        compute='_compute_partner_icon_type_detailed',
        inverse='_inverse_partner_icon_type_detailed',
        user_writeable=True,
        help='Enable this option to display detailed icons for contacts',
    )

    @api.depends('group_ids')
    def _compute_partner_icon_type_detailed(self):
        group = self.env.ref(DETAILED_ICON_GROUP, raise_if_not_found=False)
        for user in self:
            user.partner_icon_type_detailed = bool(group) and group in user.sudo().group_ids

    def _inverse_partner_icon_type_detailed(self):
        group = self.env.ref(DETAILED_ICON_GROUP)
        for user in self:
            command = Command.link if user.partner_icon_type_detailed else Command.unlink
            # the group only toggles a display preference: users may set it on
            # their own record, which record rules already restrict them to
            user.sudo().group_ids = [command(group.id)]
