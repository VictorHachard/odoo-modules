# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    breadcrumb_name = fields.Char(string='Breadcrumb Name', translate=True, related='website_id.breadcrumb_name', readonly=False)