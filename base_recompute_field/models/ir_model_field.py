# -*- coding: utf-8 -*-
import logging

from odoo import fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    can_recompute = fields.Boolean(
        compute='_compute_can_recompute',
        compute_sudo=True,
        string='Can Recompute',
        help="Indicates if the field can be recomputed using the recompute button in the model form view.",
        groups='base.group_system',
    )

    def _get_registry_field(self):
        """Return the ORM field object of this ``ir.model.fields`` record, or None
        when its model or field is not loaded in the registry."""
        self.ensure_one()
        model = self.env.get(self.model)
        return model._fields.get(self.name) if model is not None else None

    def _compute_can_recompute(self):
        for record in self:
            field = record._get_registry_field()
            record.can_recompute = bool(field and field.compute and field.store)

    def recompute_field(self):
        """Recompute the stored computed field on every record of its model,
        archived and other-company records included."""
        if not self.env.is_system():
            raise AccessError(self.env._("Only administrators can recompute fields."))
        for record in self:
            field = record._get_registry_field()
            if not (field and field.compute and field.store):
                raise UserError(self.env._(
                    "The field %(field)s of %(model)s is not a stored computed field.",
                    field=record.name, model=record.model,
                ))
            model = self.env[record.model].sudo().with_context(active_test=False)
            records = model.search([])
            _logger.info("Recomputing field %s on %d records of model %s (requested by uid %s)",
                         record.name, len(records), model._name, self.env.uid)
            self.env.add_to_compute(field, records)
            records.flush_recordset([record.name])
        return True
