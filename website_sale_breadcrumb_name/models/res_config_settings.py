# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    breadcrumb_name = fields.Char(related='website_id.breadcrumb_name', readonly=False)
