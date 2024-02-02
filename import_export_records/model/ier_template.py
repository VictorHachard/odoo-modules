# -*- coding: utf-8 -*-
import base64
import io
import json
import zipfile
from datetime import datetime, timezone

from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import pytz, get_lang
from odoo.tools.safe_eval import test_python_expr


IER_DEFAULT_POST_PROCESS_PYTHON_CODE = """# Available variables:
#  - env
#  - records_by_model: recordset by model of all imported records; may be void, e.g. {'sale.order': records, ...}
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - UserError: Warning Exception to use with raise
#  - uid, user: current user id and user record\n\n"""
IER_DEFAULT_PRE_PROCESS_PYTHON_CODE = """# Available variables:
#  - env
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - UserError: Warning Exception to use with raise
#  - uid, user: current user id and user record\n\n"""


class IERTemplate(models.Model):
    _name = 'ier.template'
    _description = 'IER Template'

    name = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True,
                              help="The user who created this template.")
    lines = fields.One2many('ier.template.line', 'ier_template_id', context={'active_test': False})
    model_ids = fields.Many2many('ir.model', compute='_compute_model_ids', string='Models',
                                 help="The models that are used in this template.")
    post_process_code = fields.Text(string='Post Process Python Code', default=IER_DEFAULT_POST_PROCESS_PYTHON_CODE,
                                    help="The post-processing code will execute once all records have been imported. You can choose whether it needs to run during the import process.")
    pre_process_code = fields.Text(string='Pre Process Python Code', default=IER_DEFAULT_PRE_PROCESS_PYTHON_CODE,
                                   help="The pre-processing code will execute before any records are imported. You can choose whether it needs to run during the import process.")

    ier_template_action_history_ids = fields.One2many('ier.template.action.history', 'ier_template_id')
    ier_template_action_history_count = fields.Integer(compute='_compute_ier_template_action_history_count')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Template name already exists !"),
    ]

    @api.constrains('post_process_code')
    def _check_post_process_code_python_code(self):
        for action in self.sudo().filtered('post_process_code'):
            msg = test_python_expr(expr=action.post_process_code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.constrains('pre_process_code')
    def _check_pre_process_code_python_code(self):
        for action in self.sudo().filtered('pre_process_code'):
            msg = test_python_expr(expr=action.pre_process_code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.depends('ier_template_action_history_ids')
    def _compute_ier_template_action_history_count(self):
        for record in self:
            record.ier_template_action_history_count = len(record.ier_template_action_history_ids)

    @api.depends('lines.model_id')
    def _compute_model_ids(self):
        for rec in self:
            rec.model_ids = rec.lines.model_id.ids

    def open_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('History'),
            'res_model': 'ier.template.action.history',
            'view_mode': 'tree,form',
            'domain': [('ier_template_id', '=', self.id)],
        }

    def _get_user_formatted_datetime(self):
        """ Get the current datetime formatted string according to the user's time zone and language settings. """
        tz = self.env.context.get('tz', 'UTC')
        lang = get_lang(self.env)
        strftime_pattern = ("%s-%s" % (lang.date_format, lang.time_format)).replace('_', '-')
        datetime_str = datetime.now(timezone.utc).astimezone(pytz.timezone(tz)).strftime(strftime_pattern)
        return datetime_str

    def _get_manifest(self):
        active_lines = self.lines.filtered(lambda l: l.active)
        return {
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'dbname': self.env.cr.dbname,
            'username': self.env.user.name,
            'userlogin': self.env.user.login,
            'ir_exports': [{
                'name': e.name,
                'model_name': e.resource,
                'fields': e.export_fields.mapped('name'),
            } for e in active_lines.mapped('ir_exports_id')],
            'post_process_code': self.post_process_code,
            'pre_process_code': self.pre_process_code,
        }

    def export(self):
        """
        Prepares and exports data in CSV format for current template.
        It then compresses the CSV files into a ZIP archive and creates an attachment for download.
        """
        self.ensure_one()
        self.lines._check_ir_exports_id()
        datetime_str = self._get_user_formatted_datetime()
        manifest = self._get_manifest()
        record_count_total = 0

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w") as zip_archive:
            for line in self.lines.filtered(lambda l: l.active):
                date, record_count = line.export_files()
                record_count_total += record_count
                zip_archive.writestr(line.file_name + '.csv', date)
            manifest['record_count'] = record_count_total
            zip_archive.writestr('manifest.json', json.dumps(manifest, indent=2))

        zip_filename = self.name.lower().replace(' ', '-') + '-' + datetime_str + '.zip'

        attachment_id = self.env['ir.attachment'].create({
            'name': zip_filename,
            'datas': base64.b64encode(zip_buffer.getvalue()),
            'res_model': 'ier.template',
            'res_id': self.id
        })
        self.env['ir.attachment']._file_delete(attachment_id.store_fname)

        self.env['ier.template.action.history'].create({
            'type': 'export',
            'ier_template_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(attachment_id.id) +
                   "&filename_field=name&field=datas&download=true&name=" + attachment_id.name,
            'target': 'self',
        }

    def copy_data(self, default=None):
        default = dict(default or {})
        if 'lines' not in default:
            default['lines'] = [(0, 0, line.copy_data()[0]) for line in self.lines]
        return super().copy_data(default)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (Copy)") % self.name
        return super().copy(default=default)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_ier_exports_ier(self):
        ier_exports_ier = self.env.ref('import_export_records.ier_exports_ier')
        if ier_exports_ier in self:
            raise UserError(_("You cannot delete this template."))
