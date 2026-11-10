# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    breadcrumb_name = fields.Char(
        string='Breadcrumb Name',
        translate=True,
        help="Replaces 'All products' in the breadcrumb of the product page.",
    )
