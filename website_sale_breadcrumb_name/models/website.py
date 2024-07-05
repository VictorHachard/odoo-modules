# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Website(models.Model):
    _inherit = 'website'

    breadcrumb_name = fields.Char(string='Breadcrumb Name', translate=True, help='Name of the breadcrumb in the website.')
