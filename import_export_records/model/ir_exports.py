# -*- coding: utf-8 -*-
from odoo import models


class IRExports(models.Model):
    _inherit = 'ir.exports'

    def _compute_display_name(self):
        if self.env.context.get('show_model', False):
            for rec in self:
                rec.display_name = f"{rec.name} ({rec.resource})"
        return super()._compute_display_name()
