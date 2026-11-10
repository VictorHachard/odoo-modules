# -*- coding: utf-8 -*-
import csv
import io

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr


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


def _check_python_code(code):
    """ Raise a ValidationError when ``code`` cannot be run by safe_eval. """
    if not code:
        return
    try:
        msg = test_python_expr(expr=code.strip(), mode="exec")
    except NameError as e:  # forbidden (dunder) names are reported this way
        msg = str(e)
    if msg:
        raise ValidationError(msg)


def _ier_eval_context(env):
    """ Base evaluation context of the template Python code and domains. """
    eval_context = env['ir.actions.actions']._get_eval_context()
    eval_context.update({
        'env': env,
        'UserError': UserError,
    })
    return eval_context


class IERTemplateLine(models.Model):
    _name = 'ier.template.line'
    _description = 'IER Template Line'
    _order = 'sequence, id'

    def _default_sequence(self):
        record = self.search([], limit=1, order="sequence DESC")
        return record.sequence + 1 if record else 1

    sequence = fields.Integer(default=_default_sequence,
                              help='The order of the line is important. If one line depends on another, make sure to place the dependent line above the one it relies on.')
    active = fields.Boolean(default=True, help='Only active lines will be included in the export.')
    ier_template_id = fields.Many2one('ier.template', required=True, index=True, ondelete='cascade')
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

    @api.depends('ir_exports_id.name', 'model_id.name')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"{line.ir_exports_id.name} ({line.model_id.name})"

    @api.constrains('code')
    def _check_code(self):
        for line in self.sudo():
            _check_python_code(line.code)

    @api.depends('model_name', 'sequence')
    def _compute_file_name(self):
        for rec in self:
            rec.file_name = f"{rec.sequence}.{rec.model_name}" if rec.model_name else False

    @api.depends('ir_exports_id.export_fields')
    def _compute_line_ids(self):
        for rec in self:
            rec.line_ids = rec.ir_exports_id.export_fields

    @api.constrains('ir_exports_id')
    def _check_ir_exports_id(self):
        if self.env.context.get('bypass_import_compat_constrain'):
            return
        for record in self:
            import_compat_fields = record._get_import_compat_for_model()
            not_allowed_fields = [
                name for name in record._get_export_fields()
                if name.split('@', 1)[0] not in import_compat_fields
            ]
            if not_allowed_fields:
                raise ValidationError(self.env._(
                    "The following fields are not importable: %s. Please check your export settings and try again.",
                    ', '.join(not_allowed_fields),
                ))

    @api.model
    def _get_importable_fields(self, model_name):
        """ Return ``{field name: field description}`` of the fields of
        ``model_name`` that an import-compatible export can contain. """
        fields_info = self.env[model_name].fields_get(attributes=['type', 'readonly', 'relation', 'exportable'])
        return {
            name: info for name, info in fields_info.items()
            if info.get('exportable', True) and (name == 'id' or not info.get('readonly'))
        }

    def _get_import_compat_for_model(self):
        """
        Return the set of import-compatible field paths of the line's model, including
        the fields of the related models; mirrors the import-compatible export dialog
        (at most two levels deep). It is used to validate export field compatibility.
        """
        self.ensure_one()
        if not self.model_name or self.model_name not in self.env:
            return set()
        allowed = {'id'}
        for name, info in self._get_importable_fields(self.model_name).items():
            ftype = info.get('type')
            if ftype in ('many2one', 'many2many'):
                allowed |= {name, f'{name}/id', f'{name}/name'}
            elif ftype == 'one2many':
                allowed |= {name, f'{name}/id'}
                for sub_name, sub_info in self._get_importable_fields(info['relation']).items():
                    sub_type = sub_info.get('type')
                    if sub_type in ('many2one', 'many2many'):
                        allowed |= {f'{name}/{sub_name}/id', f'{name}/{sub_name}/name'}
                    elif sub_type != 'one2many' and sub_name != 'id':
                        allowed.add(f'{name}/{sub_name}')
            else:
                allowed.add(name)
        return allowed

    @api.depends('ir_exports_id.resource')
    def _compute_model_id(self):
        for rec in self:
            resource = rec.ir_exports_id.resource
            rec.model_id = self.env['ir.model']._get(resource) if resource else False
            rec.model_name = resource or False

    @api.onchange('ir_exports_id')
    def _onchange_ir_exports_id(self):
        self.filter_domain = False

    def _get_domain(self):
        """ Return the domain of the ``filter_domain`` field, evaluated safely. """
        self.ensure_one()
        if not self.filter_domain:
            return []
        return safe_eval(self.filter_domain, _ier_eval_context(self.env))

    def _get_export_fields(self):
        """ Return a list of export field names associated with the 'ir_exports_id.export_fields' field. """
        return self.ir_exports_id.export_fields.mapped('name')

    def _export_template(self):
        """
        Exports data based on the current record's configuration.
        It either executes the Python code or the filtered domain based on the mode.
        """
        self.ensure_one()
        if not self.model_name or self.model_name not in self.env:
            raise UserError(self.env._("The model of the export %s is not installed.", self.ir_exports_id.display_name))

        model = self.env[self.model_name]

        if self.mode == 'advanced':
            action = self.run()
            if not action or 'records' not in action:
                raise UserError(self.env._("The action is empty. Return records in an ID list, assign: action = {'records': [ids]}"))
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
        writer.writerow(self._get_export_fields())
        for data in datas:
            writer.writerow(['' if d is False or d is None else str(d) for d in data])
        return csv_file.getvalue(), record_count

    def _get_eval_context(self):
        """ Prepares an evaluation context with various variables and libraries that can be used when executing Python code. """
        self.ensure_one()
        model = self.env[self.model_name]
        eval_context = _ier_eval_context(self.env)
        eval_context.update({
            'model': model,
            'records': model.search([]),
        })
        return eval_context

    def run(self):
        """
        Execute the Python code of the line and return the 'action' dictionary
        it assigned, or False if no action is defined.
        """
        self.ensure_one()
        eval_context = self._get_eval_context()
        safe_eval(self.code.strip(), eval_context, mode="exec", filename=str(self))
        return eval_context.get('action') or False
