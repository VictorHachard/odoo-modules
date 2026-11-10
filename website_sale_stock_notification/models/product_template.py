# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    out_of_stock_back_in_stock_message = fields.Boolean(
        string="Back in Stock Message",
        default=True,
        help="When the product is out of stock, let website visitors subscribe to an email"
             " notification sent when it is back in stock.",
    )
