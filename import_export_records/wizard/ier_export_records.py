# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IERExportWizard(models.TransientModel):
    _name = 'ier.export.wizard'
    _description = 'IER Export Wizard'

    template_id = fields.Many2one('ier.template', required=True)
    line_ids = fields.Many2many('ier.template.line', compute='_compute_line_ids')

    def export_action(self):
        self.ensure_one()
        return self.template_id.export()

    @api.depends('template_id')
    def _compute_line_ids(self):
        for rec in self:
            rec.write({'line_ids': [(6, 0, rec.template_id.lines.ids)]})
