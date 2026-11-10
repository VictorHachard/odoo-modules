# -*- coding: utf-8 -*-

from odoo import api, fields, models

ADDRESS_TYPES = ('invoice', 'delivery', 'other')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    icon_type_selection = fields.Selection([
        ('individual', 'Individual'),
        ('employee', 'Employee'),
        ('company', 'Company'),
        ('contact', 'Contact'),
        ('invoice', 'Invoice Address'),
        ('delivery', 'Delivery Address'),
        ('other', 'Other Address'),
    ],
        string='Contact type', compute='_compute_icon_type_selection', index=True, store=True
    )

    icon_type_selection_easy = fields.Selection([
        ('individual', 'Individual'),
        ('employee', 'Employee'),
        ('company', 'Company'),
        ('contact', 'Contact'),
    ],
        string='Contact type easy', compute='_compute_icon_type_selection', index=True, store=True
    )

    @api.depends('is_company', 'parent_id.is_company', 'type')
    def _compute_icon_type_selection(self):
        for rec in self:
            if rec.is_company:
                detailed = easy = 'company'
            elif rec.type in ADDRESS_TYPES:
                detailed, easy = rec.type, 'contact'
            elif not rec.parent_id:
                detailed = easy = 'individual'
            elif rec.parent_id.is_company:
                detailed = easy = 'employee'
            else:
                detailed = easy = 'contact'
            rec.icon_type_selection = detailed
            rec.icon_type_selection_easy = easy
