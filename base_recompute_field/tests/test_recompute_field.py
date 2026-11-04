# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestRecomputeField(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Fields = cls.env['ir.model.fields']
        cls.complete_name = cls.Fields._get('res.partner', 'complete_name')
        cls.partner = cls.env['res.partner'].create({'name': 'Recompute Me'})
        # an access-rights manager can write on ir.model.fields
        cls.manager = new_test_user(cls.env, login='recompute_manager', groups='base.group_user,base.group_erp_manager')

    def test_recompute_restores_values(self):
        self.partner.flush_recordset()
        self.env.cr.execute("UPDATE res_partner SET complete_name = 'corrupted' WHERE id = %s", [self.partner.id])
        self.partner.invalidate_recordset(['complete_name'])
        self.assertEqual(self.partner.complete_name, 'corrupted')
        self.complete_name.recompute_field()
        self.env.flush_all()
        self.partner.invalidate_recordset(['complete_name'])
        self.assertEqual(self.partner.complete_name, 'Recompute Me')

    def test_recompute_requires_system_group(self):
        with self.assertRaises(AccessError):
            self.complete_name.with_user(self.manager).recompute_field()

    def test_button_only_for_system(self):
        arch = self.Fields.get_view(view_type='form')['arch']
        self.assertIn('recompute_field', arch)
        arch = self.Fields.with_user(self.manager).get_view(view_type='form')['arch']
        self.assertNotIn('recompute_field', arch)
