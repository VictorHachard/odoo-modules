# -*- coding: utf-8 -*-
import csv
import io
import json
import logging
import zipfile

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.binary import BinaryBytes
from odoo.tools.safe_eval import safe_eval

from ..model.ier_template_line import _ier_eval_context


_logger = logging.getLogger(__name__)

MESSAGES_TABLE_HEADER = Markup("<table><tr><th>Model</th><th>Field</th><th>Record</th><th>Message</th></tr>")


class IERImportWizard(models.TransientModel):
    _name = 'ier.import.wizard'
    _description = 'IER Import Wizard'

    zip_file = fields.Binary(string='Upload your File', required=True, attachment=False)
    zip_file_name = fields.Char("File Name", required=True)

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
            "name": self.env._("IER Import Wizard"),
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def _open_archive(self):
        """ Return the uploaded file as an open ``ZipFile``, or None when the
        file is not a ZIP archive. """
        self.ensure_one()
        content = self.zip_file.content if self.zip_file else b''
        buffer = io.BytesIO(content)
        if not content or not zipfile.is_zipfile(buffer):
            return None
        return zipfile.ZipFile(buffer, mode="r")

    def _import_record_and_execute(self, model, csv_content, fields):
        """ Import a CSV file into ``model`` through ``base_import``. """
        import_record = self.env['base_import.import'].create({
            'res_model': model,
            'file': BinaryBytes(csv_content),
            'file_type': 'text/csv',
            'file_name': model + '.csv',
        })
        return import_record.execute_import(
            fields,
            fields,
            {'quoting': '"', 'separator': ',', 'has_headers': True},
            False,
        )

    @api.depends('zip_file')
    def _compute_manifest_data(self):
        for rec in self:
            rec.update({
                'manifest_datetime': False,
                'manifest_dbname': False,
                'manifest_username': False,
                'manifest_userlogin': False,
                'manifest_record_count': 0,
                'manifest_post_process_code': False,
                'manifest_pre_process_code': False,
                'is_importable': False,
                'manifest': False,
            })
            archive = rec._open_archive()
            if archive is None:
                continue
            with archive:
                if 'manifest.json' not in archive.namelist():
                    continue
                try:
                    data = json.loads(archive.read('manifest.json'))
                except ValueError:
                    _logger.info("Invalid manifest.json in uploaded archive %s", rec.zip_file_name)
                    continue
            if isinstance(data, dict):
                rec._set_manifest_field(data)

    def _set_manifest_field(self, data):
        self.update({
            'manifest_datetime': data.get('datetime', False),
            'manifest_dbname': data.get('dbname', False),
            'manifest_username': data.get('username', False),
            'manifest_userlogin': data.get('userlogin', False),
            'manifest_record_count': data.get('record_count', 0),
            'manifest_post_process_code': data.get('post_process_code', False),
            'manifest_pre_process_code': data.get('pre_process_code', False),
            'is_importable': True,
            'manifest': json.dumps(data),
        })

    @api.model
    def _get_csv_model_name(self, file_name):
        """ ``<sequence>.<model>.csv`` -> ``<model>`` """
        return '.'.join(file_name.split('.')[1:-1])

    def _format_messages(self, model_name, messages):
        """ Return the (error rows, warning rows) of base_import messages as HTML. """
        error_rows, warning_rows = Markup(), Markup()
        for msg in messages:
            if msg.get('field'):
                row = Markup("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n") % (
                    model_name, msg['field'], msg.get('record') or '', msg.get('message') or '')
            else:
                row = Markup("<tr><td colspan='3'>%s</td><td>%s</td></tr>\n") % (model_name, msg.get('message') or '')
            if msg.get('type') == 'error':
                error_rows += row
            elif msg.get('type') == 'warning':
                warning_rows += row
        return error_rows, warning_rows

    def import_action(self):
        self.ensure_one()
        archive = self._open_archive()
        if archive is None or not self.is_importable:
            raise UserError(self.env._("The uploaded file is not an archive exported by an import/export template."))

        record_count = 0
        records_by_model = {}
        error_html, warning_html = Markup(), Markup()

        if self.run_pre_process_code:
            self._run_code(self.manifest_pre_process_code)

        with archive:
            csv_names = sorted(
                (name for name in archive.namelist() if name.endswith('.csv')),
                key=lambda name: (int(name.split('.', 1)[0]) if name.split('.', 1)[0].isdigit() else 0, name),
            )
            for file_name in csv_names:
                model_name = self._get_csv_model_name(file_name)
                if model_name not in self.env:
                    raise UserError(self.env._("The archive contains records of the model %s, which is not installed.", model_name))
                csv_content = archive.read(file_name)
                headers = next(csv.reader(io.StringIO(csv_content.decode('utf-8'))), [])
                if not headers:
                    continue
                result = self._import_record_and_execute(model_name, csv_content, headers)
                ids = result.get('ids') or []
                record_count += len(ids)
                records_by_model[model_name] = records_by_model.get(model_name, self.env[model_name]) | self.env[model_name].browse(ids)

                errors, warnings = self._format_messages(model_name, result.get('messages') or [])
                error_html += errors
                warning_html += warnings

        if self.run_post_process_code:
            self._run_code(self.manifest_post_process_code, records_by_model=records_by_model)

        self.write({
            'error_html': MESSAGES_TABLE_HEADER + error_html + Markup("</table>") if error_html else False,
            'warning_html': MESSAGES_TABLE_HEADER + warning_html + Markup("</table>") if warning_html else False,
            'success_html': Markup("<p>%s</p>") % self.env._("%s records successfully imported", record_count),
        })

        self.env['ier.template.action.history'].create({
            'type': 'import',
            'template_name': self.zip_file_name,
            'manifest': self.manifest,
        })

        return self._reopen_self()

    def _get_eval_context(self):
        """ Prepares an evaluation context with various variables and libraries that can be used when executing Python code. """
        return _ier_eval_context(self.env)

    def _run_code(self, code, **values):
        """ Execute the pre/post process Python ``code`` of the manifest. """
        self.ensure_one()
        if not code or not code.strip():
            return
        eval_context = self._get_eval_context()
        eval_context.update(values)
        safe_eval(code.strip(), eval_context, mode="exec", filename=str(self))
