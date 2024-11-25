# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    icon_type_selection = fields.Selection([
        ('individual', 'Individual'),
        ('employee', 'Employee'),
        ('company', 'Company'),
        ('contact', 'Contact'),
        ('invoice', 'Invoice Address'),
        ('delivery', 'Delivery Address'),
        ('private', 'Private Address'),
        ('other', 'Other Address')
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
                rec.icon_type_selection = 'company'
                rec.icon_type_selection_easy = 'company'
            elif rec.type == 'invoice':
                rec.icon_type_selection = 'invoice'
                rec.icon_type_selection_easy = 'contact'
            elif rec.type == 'delivery':
                rec.icon_type_selection = 'delivery'
                rec.icon_type_selection_easy = 'contact'
            elif rec.type == 'private':
                rec.icon_type_selection = 'private'
                rec.icon_type_selection_easy = 'contact'
            elif rec.type == 'other':
                rec.icon_type_selection = 'other'
                rec.icon_type_selection_easy = 'contact'
            elif not rec.is_company and not rec.parent_id:
                rec.icon_type_selection = 'individual'
                rec.icon_type_selection_easy = 'individual'
            elif rec.parent_id and rec.parent_id.is_company:
                rec.icon_type_selection = 'employee'
                rec.icon_type_selection_easy = 'employee'
            else:
                rec.icon_type_selection = 'contact'
                rec.icon_type_selection_easy = 'contact'
