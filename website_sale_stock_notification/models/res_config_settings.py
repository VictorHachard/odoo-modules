# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    out_of_stock_back_in_stock_message = fields.Boolean(string='Back in Stock Message', default=True)

    def set_values(self):
        super().set_values()
        IrDefault = self.env['ir.default'].sudo()

        IrDefault.set('product.template', 'out_of_stock_back_in_stock_message', self.out_of_stock_back_in_stock_message)

    @api.model
    def get_values(self):
        res = super().get_values()
        IrDefaultGet = self.env['ir.default'].sudo()._get
        out_of_stock_back_in_stock_message = IrDefaultGet('product.template', 'out_of_stock_back_in_stock_message')

        res.update(
            out_of_stock_back_in_stock_message=out_of_stock_back_in_stock_message if out_of_stock_back_in_stock_message is not None else True,
        )
        return res
