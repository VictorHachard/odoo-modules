# -*- coding: utf-8 -*-
import base64
import csv
import io
import json
import zipfile
import logging

from pytz import timezone

import odoo
from odoo import models, fields, exceptions, _, api, tools
from odoo.tools import pycompat, safe_eval
from odoo.tools.safe_eval import safe_eval
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class IERImportWizard(models.TransientModel):
    _name = 'ier.import.wizard'
    _description = 'IER Import Wizard'

    zip_file = fields.Binary(string='Upload your File', required=True)
    zip_file_name = fields.Char("File Name")

    run_post_process_code = fields.Boolean(default=True, help="Run the post process code after import")
    run_pre_process_code = fields.Boolean(default=True, help="Run the pre process code before import")

    error_html = fields.Html()
    warning_html = fields.Html()
    success_html = fields.Html()

    # Manifest
    is_importable = fields.Boolean(compute='_compute_manifest_data', store=True)
    manifest = fields.Text(compute='_compute_manifest_data', store=True)
    manifest_datetime = fields.Datetime(compute='_compute_manifest_data', string='Created At', store=True)
    manifest_dbname = fields.Char(compute='_compute_manifest_data', string='From Database', store=True)
    manifest_username = fields.Char(compute='_compute_manifest_data', string='By User', store=True)
    manifest_userlogin = fields.Char(compute='_compute_manifest_data', store=True)
    manifest_record_count = fields.Integer(compute='_compute_manifest_data', store=True)
    manifest_post_process_code = fields.Text(compute='_compute_manifest_data', store=True)
    manifest_pre_process_code = fields.Text(compute='_compute_manifest_data', store=True)

    def _reopen_self(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "name": self._description,
            "view_mode": "form",
            "target": "new",
        }

    def _import_record_and_execute(self, model, decoded_csv, fields):
        """
        Import record and execute the action
        """
        import_record = self.env['base_import.import'].create({
            'res_model': model,
            'file': decoded_csv,
            'file_type': 'text/csv',
            'file_name': model,
        })
        result = import_record.execute_import(
            fields,
            fields,
            {'quoting': '"', 'separator': ',', 'has_headers': True},
            False
        )
        return result

    @api.depends('zip_file')
    def _compute_manifest_data(self):
        for rec in self:
            rec.update({
                'manifest_datetime': False,
                'manifest_dbname': '',
                'manifest_username': '',
                'manifest_userlogin': '',
                'manifest_record_count': 0,
                'manifest_post_process_code': '',
                'manifest_pre_process_code': '',
                'is_importable': False,
                'manifest': '',
            })
            if rec.zip_file:
                decoded_zip = base64.b64decode(rec.zip_file)
                io_bytes_zip = io.BytesIO(decoded_zip)

                if zipfile.is_zipfile(io_bytes_zip):
                    with zipfile.ZipFile(io_bytes_zip, mode="r") as archive:
                        manifest_content = next((archive.read(name) for name in archive.namelist() if name == "manifest.json"), None)
                        if manifest_content is not None:
                            rec._set_manifest_field(json.loads(manifest_content))

    def _set_manifest_field(self, data):
        self.update({
            'manifest_datetime': data.get('datetime', False),
            'manifest_dbname': data.get('dbname', ''),
            'manifest_username': data.get('username', ''),
            'manifest_userlogin': data.get('userlogin', ''),
            'manifest_record_count': data.get('record_count', 0),
            'manifest_post_process_code': data.get('post_process_code', ''),
            'manifest_pre_process_code': data.get('pre_process_code', ''),
            'is_importable': True,
            'manifest': json.dumps(data).encode('utf-8'),
        })

    def import_action(self):
        self.ensure_one()
        if self.zip_file:
            self.success_html = False
            error_html, warning_html = '', ''

            record_count = 0
            records_by_model = {}
            decoded_zip = base64.b64decode(self.zip_file)
            io_bytes_zip = io.BytesIO(decoded_zip)

            if self.run_pre_process_code:
                self._run_pre_process_code()

            if zipfile.is_zipfile(io_bytes_zip):
                with zipfile.ZipFile(io_bytes_zip, mode="r") as archive:
                    csv_files = {name: archive.read(name) for name in archive.namelist() if '.csv' in name}
                    for model, csv_file in csv_files.items():
                        decoded_csv = csv_file.decode()
                        headers = next(csv.reader(io.StringIO(decoded_csv)))
                        model_name = '.'.join(model.split('.')[1:-1])
                        result = self._import_record_and_execute(model_name, decoded_csv, headers)
                        record_count += len(result['ids']) if result['ids'] else 0
                        if model_name not in records_by_model:
                            records_by_model[model_name] = self.env[model_name].browse(result['ids'])
                        else:
                            records_by_model[model_name] += self.env[model_name].browse(result['ids'])

                        if result and 'messages' in result and len(result['messages']) > 0:
                            for msg in result['messages']:
                                if msg['field']:
                                    html_row = f"<tr><td>{model_name}</td><td>{msg['field']}</td><td>{msg['record']}</td><td>{msg['message']}</td></tr>\n"
                                else:
                                    html_row = f"<tr><td colspan='3'>{model_name}</td><td>{msg['message']}</td></tr>\n"
                                error_html += html_row if msg['type'] == 'error' else ''
                                warning_html += html_row if msg['type'] == 'warning' else ''

            if self.run_post_process_code:
                self._run_post_process_code(records_by_model)
            self.error_html = "<table><tr><th>Model</th><th>Field</th><th>Record</th><th>Message</th></tr>" + error_html + "</table>" if error_html else ''
            self.warning_html = "<table><tr><th>Model</th><th>Field</th><th>Record</th><th>Message</th></tr>" + warning_html + "</table>" if warning_html else ''
            self.success_html = f"<p>{_('%s records successfully imported', str(record_count))}</p>"

            self.env['ier.template.action.history'].create({
                'type': 'import',
                'template_name': self.zip_file_name,
                'manifest': self.manifest,
            })

            return self._reopen_self()

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
            # Exceptions
            'Warning': odoo.exceptions.Warning,
            'UserError': odoo.exceptions.UserError,
        }

    def _run_action_code_multi(self, eval_context):
        """ Executes the Python code within the provided evaluation context. """
        safe_eval(self.manifest_post_process_code.strip(), eval_context, mode="exec", nocopy=True, filename=str(self))  # nocopy allows to return 'action'

    def _run_post_process_code(self, records_by_model):
        """
        Orchestrates the execution of Python code.
        It handles access control, evaluation context setup, and code execution, returning the 'action' dictionary from the code execution, or False if no action is defined.
        """
        self.ensure_one()
        eval_context = self._get_eval_context()
        eval_context['records_by_model'] = records_by_model
        # if records:
        #     try:
        #         records.check_access_rule('write')
        #     except AccessError:
        #         _logger.warning("Forbidden server action %r executed while the user %s does not have access to %s.",
        #                         self.display_name, self.env.user.login, records,)
        #         raise
        run_self = self.with_context(eval_context['env'].context)
        run_self._run_action_code_multi(eval_context=eval_context)

    def _run_pre_process_code(self):
        """
        Orchestrates the execution of Python code.
        It handles access control, evaluation context setup, and code execution, returning the 'action' dictionary from the code execution, or False if no action is defined.
        """
        self.ensure_one()
        eval_context = self._get_eval_context()
        # if records:
        #     try:
        #         records.check_access_rule('write')
        #     except AccessError:
        #         _logger.warning("Forbidden server action %r executed while the user %s does not have access to %s.",
        #                         self.display_name, self.env.user.login, records,)
        #         raise
        run_self = self.with_context(eval_context['env'].context)
        run_self._run_action_code_multi(eval_context=eval_context)