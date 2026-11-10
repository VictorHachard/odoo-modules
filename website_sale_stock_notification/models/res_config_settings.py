# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_out_of_stock_back_in_stock_message = fields.Boolean(
        string='Back in Stock Message',
        default=True,
        default_model='product.template',
    )
