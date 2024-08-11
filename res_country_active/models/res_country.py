# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCountry(models.Model):
    _inherit = 'res.country'

    active = fields.Boolean(default=True)
