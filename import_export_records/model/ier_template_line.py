# -*- coding: utf-8 -*-
import csv
import io
import logging

from pytz import timezone

import odoo
from odoo import api, fields, models, tools, _
from odoo.addons.web.controllers.export import Export
from odoo.exceptions import MissingError, ValidationError, AccessError, UserError
from odoo.tools import pycompat, safe_eval
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


IER_DEFAULT_PYTHON_CODE = """# Available variables:
#  - env
#  - model: current model
#  - records: recordset of all records from the model; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - UserError: Warning Exception to use with raise
#  - uid, user: current user id and user record
# Return records in an ID list, assign: action = {'records': [ids]}\n\n
action = {'records': records.ids}\n"""


class IERTemplateLine(models.Model):
    _name = 'ier.template.line'
    _description = 'IER Template Line'

    def _default_sequence(self):
        record = self.search([], limit=1, order="sequence DESC")
        return record.sequence + 1 if record else 1

    sequence = fields.Integer(default=_default_sequence,
                              help='The order of the line is important. If one line depends on another, make sure to place the dependent line above the one it relies on.')
    active = fields.Boolean(default=True, help='Only active lines will be included in the export.')
    ier_template_id = fields.Many2one('ier.template', required=True, ondelete='cascade')
    ir_exports_id = fields.Many2one('ir.exports', required=True, string='Exports Template', ondelete='cascade',
                                    help='The export template must be a import-compatible export and should not contain fields nested more than two levels deep.')

    model_id = fields.Many2one('ir.model', compute='_compute_model_id', store=True)
    model_name = fields.Char(compute='_compute_model_id', store=True)
    file_name = fields.Char(compute='_compute_file_name', store=True)

    mode = fields.Selection([('easy', 'Simple'), ('advanced', 'Advanced')], required=True, default='easy',
                            help='Simple mode allows you to select records based on a domain. Advanced mode allows you to write Python code to select the records for export.')
    filter_domain = fields.Char(help='domain to select the records for exporting')
    code = fields.Text(string='Python Code', default=IER_DEFAULT_PYTHON_CODE,
                       help="Python code to select the records for exporting.")

    line_ids = fields.Many2many('ir.exports.line', compute='_compute_line_ids', help='The export fields associated with the ir.exports template.')

    def _compute_display_name(self):
        for template in self:
            template.display_name = f"{template.ir_exports_id.name} ({template.model_id.name})"

    @api.constrains('code')
    def _check_python_code(self):
        for action in self.sudo().filtered('code'):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.depends('model_name', 'sequence')
    def _compute_file_name(self):
        for rec in self:
            rec.file_name = str(rec.sequence) + '.' + rec.model_name

    @api.depends('ir_exports_id')
    def _compute_line_ids(self):
        for rec in self:
            rec.write({'line_ids': [(6, 0, rec.ir_exports_id.export_fields.ids)]})

    @api.constrains('ir_exports_id')
    def _check_ir_exports_id(self):
        if self.env.context.get('bypass_import_compat_constrain', False):
            return
        for record in self:
            not_allowed_fields = []
            import_compat_fields = record._get_import_compat_for_model()
            for field in record.ir_exports_id.export_fields.mapped('name'):
                if field not in import_compat_fields:
                    not_allowed_fields.append(field)
            if not_allowed_fields:
                raise ValidationError(
                    _('The following fields are not importable: %s. Please check your export settings and try again.') % ','.join(not_allowed_fields))

    def _get_import_compat_for_model(self):
        """
        Return a list of import-compatible field names for the current model, including fields from related models.
        It is used to validate export field compatibility.
        """
        fields = (Export().get_fields(model=self.model_name))
        fields_value = [field['value'] for field in fields]
        for field in fields:
            if field['field_type'] in ['many2one', 'many2many']:
                fields_value += [field['id'], field['id'] + '/id', field['id'] + '/name']
            elif field['field_type'] in ['one2many']:
                sub_fields = (Export().get_fields(model=field['params']['model']))
                for sub_field in sub_fields:
                    if sub_field['field_type'] in ['many2one', 'many2many']:
                        fields_value += [field['id'] + '/' + sub_field['value'], field['id'] + '/' + sub_field['value'].replace('/id', '') + '/name']
                sub_fields_value = [field['id'] + '/' + sub_field['value'] for sub_field in sub_fields if sub_field['field_type'] not in ['many2one', 'many2many', 'one2many'] and sub_field['id'] != 'id']
                fields_value += sub_fields_value + [field['id']]
        return fields_value

    @api.depends('ir_exports_id')
    def _compute_model_id(self):
        for rec in self:
            if rec.ir_exports_id:
                rec.model_id = self.env['ir.model'].search([('model', '=', rec.ir_exports_id.resource)])
                rec.model_name = rec.ir_exports_id.resource
            else:
                rec.model_id = False
                rec.model_name = ''

    @api.depends('ir_exports_id')
    def _onchange_ir_exports_id(self):
        for rec in self:
            rec.filter_domain = ''

    def _get_domain(self):
        """ Return a domain expression based on the 'filter_domain' field, evaluating it using eval if it is not empty. """
        return eval(self.filter_domain) if self.filter_domain else []

    def _get_export_fields(self):
        """ Return a list of export field names associated with the 'ir_exports_id.export_fields' field. """
        return self.ir_exports_id.export_fields.mapped('name')

    def _export_template(self):
        """
        Exports data based on the current record's configuration.
        It either executes the Python code or the filtered domain based on the mode.
        """
        self.ensure_one()

        model = self.env[self.model_name]

        if self.mode == 'advanced':
            action = self.run()
            if not action or 'records' not in action:
                raise UserError(_("The action is empty. Return records in an ID list, assign: action = {'records': [ids]}"))
            records = model.browse(action['records'])
        else:
            records = model.search(self._get_domain())

        datas = records.export_data(self._get_export_fields()).get('datas', [])
        return datas, len(records)

    def export_files(self):
        """ Exports data in CSV format based on the export configuration defined in the current record. """
        self.ensure_one()

        csv_file = io.StringIO()
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        datas, record_count = self._export_template()
        writer.writerows([self._get_export_fields()])
        for data in datas:
            row = []
            for d in data:
                row.append(pycompat.to_text(d))
            writer.writerow(row)
        return csv_file.getvalue(), record_count

    @api.model
    def _get_eval_context(self):
        """ Prepares an evaluation context with various variables and libraries that can be used when executing Python code. """
        return {
            'uid': self._uid,
            'user': self.env.user,
            'time': tools.safe_eval.time,
            'datetime': tools.safe_eval.datetime,
            'dateutil': tools.safe_eval.dateutil,
            'timezone': timezone,
            'float_compare': float_compare,
            # orm
            'env': self.env,
            'model': self.env[self.model_name],
            # Exceptions
            'Warning': odoo.exceptions.Warning,
            'UserError': odoo.exceptions.UserError,
            # record
            'records': self.env[self.model_name].search([]),
        }

    def _run_action_code_multi(self, eval_context):
        """
        Executes the Python code within the provided evaluation context.
        It returns the 'action' dictionary from the code execution.
        """
        safe_eval(self.code.strip(), eval_context, mode="exec", nocopy=True, filename=str(self))  # nocopy allows to return 'action'
        return eval_context.get('action')

    def run(self):
        """
        Orchestrates the execution of Python code.
        It handles access control, evaluation context setup, and code execution, returning the 'action' dictionary from the code execution, or False if no action is defined.
        """
        self.ensure_one()
        eval_context = self._get_eval_context()
        records = eval_context.get('records')
        if records:
            try:
                records.check_access_rule('write')
            except AccessError:
                _logger.warning("Forbidden server action %r executed while the user %s does not have access to %s.",
                                self.display_name, self.env.user.login, records,)
                raise
        run_self = self.with_context(eval_context['env'].context)
        res = run_self._run_action_code_multi(eval_context=eval_context)
        return res or False
