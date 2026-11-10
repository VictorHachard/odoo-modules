# -*- coding: utf-8 -*-
from odoo import models, fields, _, api


class IERTemplateActionHistory(models.Model):
    _name = 'ier.template.action.history'
    _description = 'IER Template Action History'
    _order = 'create_date DESC'

    name = fields.Char(compute='_compute_name', store=True)
    type = fields.Selection([('export', 'Export'), ('import', 'Import')], required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True,
                              help="The user who exported this template.")

    # Export
    ier_template_id = fields.Many2one('ier.template', ondelete='cascade')

    # Import
    template_name = fields.Char()
    manifest = fields.Text(string='Manifest', readonly=True, help='The manifest of the import file.')

    @api.depends('ier_template_id', 'template_name', 'type')
    def _compute_name(self):
        for record in self:
            if record.type == 'export' and record.ier_template_id:
                record.name = f'{record.ier_template_id.name} ({record.type})'
            elif record.type == 'import' and record.template_name:
                record.name = f'{record.template_name} ({record.type})'
            else:
                record.name = ''
