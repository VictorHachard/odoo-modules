# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_all_value_numeric = fields.Boolean(compute='_compute_is_all_value_numeric', store=True)
    display_type = fields.Selection(selection_add=[('range', 'Range')], ondelete={'range': 'set default'})

    uom = fields.Char(string='Unit of Measure', help='Unit of Measure for the attribute values')
    range_display_type = fields.Selection([
        ('default', 'Default'), ('integer', 'Integer'), ('integer_no_locale', 'Integer No Locale'),
        ('float', 'Float'), ('float_no_locale', 'Float No Locale')
    ], string='Range Display Type', default='default', help='Display type for the range slider', required=True)

    @api.depends('value_ids')
    def _compute_is_all_value_numeric(self):
        for rec in self:
            is_all_value_numeric = all([v.name.isnumeric() for v in rec.value_ids])
            if is_all_value_numeric:
                rec.is_all_value_numeric = True
            else:
                rec.is_all_value_numeric = False
                rec.display_type = 'radio'
