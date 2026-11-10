# -*- coding: utf-8 -*-
import io
import json
import re
import zipfile
from datetime import datetime, timezone

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang

from .ier_template_line import _check_python_code


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
    lines = fields.One2many('ier.template.line', 'ier_template_id', context={'active_test': False}, copy=True)
    model_ids = fields.Many2many('ir.model', compute='_compute_model_ids', string='Models',
                                 help="The models that are used in this template.")
    post_process_code = fields.Text(string='Post Process Python Code', default=IER_DEFAULT_POST_PROCESS_PYTHON_CODE,
                                    help="The post-processing code will execute once all records have been imported. You can choose whether it needs to run during the import process.")
    pre_process_code = fields.Text(string='Pre Process Python Code', default=IER_DEFAULT_PRE_PROCESS_PYTHON_CODE,
                                   help="The pre-processing code will execute before any records are imported. You can choose whether it needs to run during the import process.")

    ier_template_action_history_ids = fields.One2many('ier.template.action.history', 'ier_template_id')
    ier_template_action_history_count = fields.Integer(compute='_compute_ier_template_action_history_count')

    _name_uniq = models.Constraint(
        'unique (name)',
        "Template name already exists!",
    )

    @api.constrains('post_process_code', 'pre_process_code')
    def _check_process_code(self):
        for template in self.sudo():
            _check_python_code(template.post_process_code)
            _check_python_code(template.pre_process_code)

    @api.depends('ier_template_action_history_ids')
    def _compute_ier_template_action_history_count(self):
        for record in self:
            record.ier_template_action_history_count = len(record.ier_template_action_history_ids)

    @api.depends('lines.model_id')
    def _compute_model_ids(self):
        for rec in self:
            rec.model_ids = rec.lines.model_id

    def open_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('History'),
            'res_model': 'ier.template.action.history',
            'view_mode': 'list,form',
            'domain': [('ier_template_id', '=', self.id)],
        }

    def _get_user_formatted_datetime(self):
        """ Current datetime formatted with the user's time zone and language
        settings, made safe to be used in a file name. """
        lang = get_lang(self.env)
        strftime_pattern = "%s-%s" % (lang.date_format, lang.time_format)
        datetime_str = datetime.now(timezone.utc).astimezone(self.env.tz).strftime(strftime_pattern)
        return re.sub(r'[^\w.-]+', '-', datetime_str)

    def _get_manifest(self):
        active_lines = self.lines.filtered('active')
        return {
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'dbname': self.env.cr.dbname,
            'username': self.env.user.name,
            'userlogin': self.env.user.login,
            'ir_exports': [{
                'name': e.name,
                'model_name': e.resource,
                'fields': e.export_fields.mapped('name'),
            } for e in active_lines.ir_exports_id],
            'post_process_code': self.post_process_code,
            'pre_process_code': self.pre_process_code,
        }

    def _export_zip(self):
        """ Export the active lines of the template as CSV files compressed in a
        ZIP archive, together with a ``manifest.json``.

        :return: the archive content
        :rtype: bytes
        """
        self.ensure_one()
        active_lines = self.lines.filtered('active').sorted(lambda l: (l.sequence, l.id))
        active_lines._check_ir_exports_id()
        manifest = self._get_manifest()
        record_count_total = 0

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_archive:
            for line in active_lines:
                data, record_count = line.export_files()
                record_count_total += record_count
                zip_archive.writestr(line.file_name + '.csv', data)
            manifest['record_count'] = record_count_total
            zip_archive.writestr('manifest.json', json.dumps(manifest, indent=2))
        return zip_buffer.getvalue()

    def export(self):
        """ Export the template as a ZIP archive attached to the template and
        return the action downloading it. """
        self.ensure_one()
        content = self._export_zip()
        zip_filename = '%s-%s.zip' % (re.sub(r'[^\w.-]+', '-', self.name.lower()), self._get_user_formatted_datetime())
        attachment = self.env['ir.attachment'].create({
            'name': zip_filename,
            'raw': content,
            'mimetype': 'application/zip',
            'res_model': self._name,
            'res_id': self.id,
        })

        self.env['ier.template.action.history'].create({
            'type': 'export',
            'ier_template_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not (default or {}).get('name'):
            for template, vals in zip(self, vals_list):
                vals['name'] = self.env._("%s (Copy)", template.name)
        return vals_list

    @api.ondelete(at_uninstall=False)
    def _unlink_except_ier_exports_ier(self):
        ier_exports_ier = self.env.ref('import_export_records.ier_exports_ier', raise_if_not_found=False)
        if ier_exports_ier and ier_exports_ier in self:
            raise UserError(self.env._("You cannot delete this template."))
