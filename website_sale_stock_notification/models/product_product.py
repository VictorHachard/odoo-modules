# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _can_add_to_stock_notifications(self):
        return super()._can_add_to_stock_notifications() and self.out_of_stock_back_in_stock_message
