# -*- coding: utf-8 -*-
from odoo import api, models


class IrExports(models.Model):
    _inherit = 'ir.exports'

    @api.depends_context('show_model')
    def _compute_display_name(self):
        if not self.env.context.get('show_model'):
            return super()._compute_display_name()
        for rec in self:
            rec.display_name = f"{rec.name} ({rec.resource})"
