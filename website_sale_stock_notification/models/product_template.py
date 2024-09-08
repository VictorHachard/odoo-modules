# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    out_of_stock_back_in_stock_message = fields.Boolean(string="Back in Stock Message", default=True)


    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        product_or_template = product_or_template.sudo()
        res.update({
            'out_of_stock_back_in_stock_message': product_or_template.out_of_stock_back_in_stock_message,
        })
        return res
