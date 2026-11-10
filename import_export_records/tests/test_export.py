# -*- coding: utf-8 -*-
import csv
import io
import json

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import IERCommon


@tagged('post_install', '-at_install')
class TestIERExport(IERCommon):

    def test_line_computed_fields(self):
        self.assertEqual(self.line.model_name, 'res.partner.category')
        self.assertEqual(self.line.model_id, self.env['ir.model']._get('res.partner.category'))
        self.assertEqual(self.line.file_name, '1.res.partner.category')
        self.assertEqual(self.line.line_ids, self.tag_export.export_fields)
        self.assertEqual(self.template.model_ids, self.line.model_id)
        self.assertEqual(self.line.display_name, 'IER tags (%s)' % self.line.model_id.name)

    def test_ir_exports_display_name_with_model(self):
        self.assertEqual(self.tag_export.display_name, 'IER tags')
        self.assertEqual(self.tag_export.with_context(show_model=True).display_name, 'IER tags (res.partner.category)')

    def test_export_zip_content(self):
        files = self._read_zip(self.template._export_zip())
        self.assertEqual(set(files), {'1.res.partner.category.csv', 'manifest.json'})
        rows = list(csv.reader(io.StringIO(files['1.res.partner.category.csv'])))
        self.assertEqual(rows[0], ['id', 'name', 'color', 'parent_id/id'])
        names = {row[1] for row in rows[1:]}
        self.assertEqual(names, {'IER Parent', 'IER Alpha', 'IER Beta'})
        beta = next(row for row in rows[1:] if row[1] == 'IER Beta')
        self.assertEqual(beta[3], '', "empty many2one must be exported as an empty cell, not 'False'")

        manifest = json.loads(files['manifest.json'])
        self.assertEqual(manifest['record_count'], 3)
        self.assertEqual(manifest['dbname'], self.env.cr.dbname)
        self.assertEqual(manifest['ir_exports'][0]['model_name'], 'res.partner.category')

    def test_export_action_creates_attachment_and_history(self):
        action = self.template.export()
        attachment = self.env['ir.attachment'].search([('res_model', '=', 'ier.template'), ('res_id', '=', self.template.id)])
        self.assertEqual(len(attachment), 1)
        self.assertEqual(action['url'], '/web/content/%s?download=true' % attachment.id)
        self.assertTrue(attachment.name.endswith('.zip'))
        self.assertNotRegex(attachment.name, r'[/\\: ]', "the file name must be safe to download")
        self.assertIn('manifest.json', self._read_zip(attachment.raw.content))
        self.assertEqual(self.template.ier_template_action_history_count, 1)
        self.assertEqual(self.template.ier_template_action_history_ids.name, 'IER test template (export)')

    def test_export_follows_line_sequence_and_skips_inactive(self):
        group_export = self.env['ir.exports'].create({
            'name': 'IER country groups',
            'resource': 'res.country.group',
            'export_fields': [(0, 0, {'name': 'id'}), (0, 0, {'name': 'name'})],
        })
        self.template.write({'lines': [
            (0, 0, {'sequence': 10, 'ir_exports_id': group_export.id, 'filter_domain': "[('id', '=', 0)]"}),
            (0, 0, {'sequence': 5, 'ir_exports_id': group_export.id, 'active': False}),
        ]})
        self.line.sequence = 20
        files = self._read_zip(self.template._export_zip())
        self.assertEqual(list(files), ['10.res.country.group.csv', '20.res.partner.category.csv', 'manifest.json'])

    def test_advanced_mode(self):
        self.line.write({
            'mode': 'advanced',
            'code': "action = {'records': records.filtered(lambda r: r.name == 'IER Beta').ids}",
        })
        datas, count = self.line._export_template()
        self.assertEqual(count, 1)
        self.assertEqual(datas[0][1], 'IER Beta')

    def test_advanced_mode_without_action(self):
        self.line.write({'mode': 'advanced', 'code': "x = 1"})
        with self.assertRaises(UserError):
            self.line._export_template()

    def test_invalid_python_code_rejected(self):
        with self.assertRaises(ValidationError):
            self.line.code = "import os"
        with self.assertRaises(ValidationError):
            self.template.pre_process_code = "def ("
        with self.assertRaises(ValidationError):
            self.template.post_process_code = "a.__class__"

    def test_filter_domain_is_safely_evaluated(self):
        """ filter_domain used to go through Python's builtin eval(). """
        self.line.filter_domain = "[('name', '=', __import__('os').getcwd())]"
        with self.assertRaises((NameError, ValueError)):
            self.line._get_domain()
        self.line.filter_domain = "[('create_uid', '=', uid)]"
        self.assertEqual(self.line._get_domain(), [('create_uid', '=', self.env.uid)])

    def test_import_compat_check(self):
        self.line._check_ir_exports_id()
        readonly_export = self.env['ir.exports'].create({
            'name': 'IER readonly',
            'resource': 'res.partner.category',
            'export_fields': [(0, 0, {'name': 'id'}), (0, 0, {'name': 'partner_ids/display_name'})],
        })
        with self.assertRaises(ValidationError):
            self.line.ir_exports_id = readonly_export

    def test_import_compat_check_accepts_nested_and_translations(self):
        partner_export = self.env['ir.exports'].create({
            'name': 'IER partners',
            'resource': 'res.partner',
            'export_fields': [(0, 0, {'name': name}) for name in (
                'id', 'name', 'country_id/id', 'category_id/id', 'child_ids/name', 'child_ids/country_id/id',
            )],
        })
        self.line.ir_exports_id = partner_export
        self.assertEqual(self.line.model_name, 'res.partner')
        tag_export_fr = self.env['ir.exports'].create({
            'name': 'IER tags fr',
            'resource': 'res.partner.category',
            'export_fields': [(0, 0, {'name': 'id'}), (0, 0, {'name': 'name@fr_FR'})],
        })
        self.line.ir_exports_id = tag_export_fr

    def test_onchange_export_resets_domain(self):
        self.line._onchange_ir_exports_id()
        self.assertFalse(self.line.filter_domain)

    def test_copy_template(self):
        copy = self.template.copy()
        self.assertEqual(copy.name, 'IER test template (Copy)')
        self.assertEqual(len(copy.lines), 1)
        self.assertNotEqual(copy.lines, self.template.lines)
        self.assertEqual(copy.lines.ir_exports_id, self.tag_export)

    def test_default_template(self):
        default = self.env.ref('import_export_records.ier_exports_ier')
        with self.assertRaises(UserError):
            default.unlink()
        self.template.action_archive()
        files = self._read_zip(default._export_zip())
        templates_csv = next(content for name, content in files.items() if name.endswith('.ier.template.csv'))
        exports_csv = next(content for name, content in files.items() if name.endswith('.ir.exports.csv'))
        self.assertIn('IER test template', templates_csv, "archived templates are exported too")
        self.assertNotIn('IER Template,', templates_csv, "the default template does not export itself")
        self.assertIn('IER tags', exports_csv, "the exports of archived templates are exported too")
