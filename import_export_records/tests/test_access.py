# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import IERCommon


@tagged('post_install', '-at_install')
class TestIERAccess(IERCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='ier_user', groups='base.group_user,base.group_allow_export')
        cls.erp_manager = new_test_user(cls.env, login='ier_manager', groups='base.group_user,base.group_erp_manager')
        cls.admin = new_test_user(cls.env, login='ier_admin', groups='base.group_user,base.group_system')

    def test_models_restricted_to_administrators(self):
        for user in (self.user, self.erp_manager):
            for model in ('ier.template', 'ier.template.line', 'ier.template.action.history',
                          'ier.export.wizard', 'ier.import.wizard'):
                with self.subTest(user=user.login, model=model), self.assertRaises(AccessError):
                    self.env[model].with_user(user).search([])

    def test_admin_can_export(self):
        action = self.template.with_user(self.admin).export()
        self.assertEqual(action['type'], 'ir.actions.act_url')

    def test_user_cannot_run_template_code(self):
        self.line.write({'mode': 'advanced', 'code': "action = {'records': records.ids}"})
        with self.assertRaises(AccessError):
            self.line.with_user(self.user).run()
        with self.assertRaises(AccessError):
            self.template.with_user(self.user).export()

    def test_history_is_append_only(self):
        history = self.env['ier.template.action.history'].with_user(self.admin).create({
            'type': 'export', 'ier_template_id': self.template.id,
        })
        with self.assertRaises(AccessError):
            history.write({'type': 'import'})
        with self.assertRaises(AccessError):
            history.unlink()

    def test_menu_hidden_from_internal_users(self):
        menu = self.env.ref('import_export_records.menu_root_import_export_records')
        visible = self.env['ir.ui.menu'].with_user(self.user)._visible_menu_ids()
        self.assertNotIn(menu.id, visible)
        self.assertIn(menu.id, self.env['ir.ui.menu']._visible_menu_ids())
