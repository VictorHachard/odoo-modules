# -*- coding: utf-8 -*-
import io
import json
import zipfile

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import IERCommon


@tagged('post_install', '-at_install')
class TestIERImport(IERCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ICP = cls.env['ir.config_parameter']
        cls.template.write({
            'pre_process_code': "env['ir.config_parameter'].set_str('ier.test.pre', 'done')",
            'post_process_code': (
                "env['ir.config_parameter'].set_str('ier.test.post', "
                "','.join(sorted(records_by_model['res.partner.category'].mapped('name'))))"
            ),
        })
        # external ids are needed to match the records on import
        cls.tags._export_rows([['id']])
        cls.parent_tag._export_rows([['id']])

    def test_manifest_is_read_on_upload(self):
        wizard = self._make_wizard(self.template._export_zip())
        self.assertTrue(wizard.is_importable)
        self.assertEqual(wizard.manifest_record_count, 3)
        self.assertEqual(wizard.manifest_dbname, self.env.cr.dbname)
        self.assertEqual(wizard.manifest_username, self.env.user.name)
        self.assertIn('ier.test.pre', wizard.manifest_pre_process_code)
        self.assertIn('ier.test.post', wizard.manifest_post_process_code)
        self.assertEqual(json.loads(wizard.manifest)['record_count'], 3)

    def test_not_a_zip(self):
        wizard = self._make_wizard(b'not a zip file')
        self.assertFalse(wizard.is_importable)
        with self.assertRaises(UserError):
            wizard.import_action()

    def test_zip_without_manifest(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('1.res.partner.category.csv', 'id,name\n')
        wizard = self._make_wizard(buffer.getvalue())
        self.assertFalse(wizard.is_importable)

    def test_import_roundtrip(self):
        content = self.template._export_zip()
        alpha_xmlid = self.tags[0].get_external_id()[self.tags[0].id]
        self.tags.unlink()

        wizard = self._make_wizard(content)
        action = wizard.import_action()
        self.assertEqual(action['res_id'], wizard.id)
        self.assertFalse(wizard.error_html)
        self.assertIn('3 records successfully imported', wizard.success_html)

        alpha = self.env.ref(alpha_xmlid)
        self.assertEqual(alpha.name, 'IER Alpha')
        self.assertEqual(alpha.color, 1)
        self.assertEqual(alpha.parent_id, self.parent_tag)
        self.assertTrue(self.Tag.search([('name', '=', 'IER Beta')]))

        self.assertEqual(self.ICP.get_str('ier.test.pre'), 'done')
        self.assertEqual(self.ICP.get_str('ier.test.post'), 'IER Alpha,IER Beta,IER Parent')

        history = self.env['ier.template.action.history'].search([('type', '=', 'import')], limit=1)
        self.assertEqual(history.template_name, 'test.zip')
        self.assertEqual(history.name, 'test.zip (import)')
        self.assertEqual(history.manifest, wizard.manifest)

    def test_pre_process_runs_pre_code_only(self):
        """ The pre-process step used to execute the post-process code. """
        wizard = self._make_wizard(self.template._export_zip(), run_post_process_code=False)
        wizard.import_action()
        self.assertEqual(self.ICP.get_str('ier.test.pre'), 'done')
        self.assertFalse(self.ICP.get_str('ier.test.post'))

    def test_post_process_only(self):
        wizard = self._make_wizard(self.template._export_zip(), run_pre_process_code=False)
        wizard.import_action()
        self.assertFalse(self.ICP.get_str('ier.test.pre'))
        self.assertTrue(self.ICP.get_str('ier.test.post'))

    def test_import_errors_are_reported(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('1.res.partner.category.csv', 'id,name,parent_id/id\nier_test.bad_tag,<b>Bad</b>,ier_test.missing\n')
            archive.writestr('manifest.json', json.dumps({'record_count': 1, 'ir_exports': []}))
        wizard = self._make_wizard(buffer.getvalue())
        wizard.import_action()
        self.assertTrue(wizard.error_html)
        self.assertIn('res.partner.category', wizard.error_html)
        self.assertNotIn('<b>Bad</b>', wizard.error_html, "import messages must be escaped")
        self.assertIn('0 records successfully imported', wizard.success_html)

    def test_unknown_model_in_archive(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('1.not.a.model.csv', 'id,name\nx,y\n')
            archive.writestr('manifest.json', json.dumps({'ir_exports': []}))
        wizard = self._make_wizard(buffer.getvalue())
        with self.assertRaises(UserError):
            wizard.import_action()

    def test_csv_files_imported_in_sequence_order(self):
        self.assertEqual(
            self.env['ier.import.wizard']._get_csv_model_name('12.res.partner.category.csv'),
            'res.partner.category',
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            # the child (sequence 10) references the parent (sequence 2)
            archive.writestr('10.res.partner.category.csv', 'id,name,parent_id/id\nier_test.child,IER Child,ier_test.parent\n')
            archive.writestr('2.res.partner.category.csv', 'id,name\nier_test.parent,IER New Parent\n')
            archive.writestr('manifest.json', json.dumps({'ir_exports': []}))
        wizard = self._make_wizard(buffer.getvalue())
        wizard.import_action()
        self.assertFalse(wizard.error_html)
        self.assertEqual(self.env.ref('ier_test.child').parent_id, self.env.ref('ier_test.parent'))
