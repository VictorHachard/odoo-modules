# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    can_recompute = fields.Boolean(
        compute='_compute_can_recompute',
        compute_sudo=True,
        string='Can Recompute',
        help="Indicates if the field can be recomputed using the recompute button in the model form view.",
        groups='base.group_system'
    )

    def recompute_field(self):
        # Callable through RPC by anyone with write access on ir.model.fields
        if not self.env.is_system():
            raise AccessError(_("Only administrators can recompute fields."))
        self.ensure_one()
        model = self.env[self.model_id.model]
        records = model.search([])
        _logger.info("Recomputing %d records for field %s in model %s", len(records), self.name, model._name)
        self.env.add_to_compute(model._fields[self.name], records)

    def _compute_can_recompute(self):
        for field in self:
            attrs = self.env[field.model]._fields[field.name]
            field.can_recompute = attrs.compute and attrs.store
