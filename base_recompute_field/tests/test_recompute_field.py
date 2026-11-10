# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestRecomputeField(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Fields = cls.env['ir.model.fields']
        cls.complete_name = cls.Fields._get('res.partner', 'complete_name')
        cls.partner_name = cls.Fields._get('res.partner', 'name')
        cls.partner = cls.env['res.partner'].create({'name': 'Recompute Active'})
        cls.archived = cls.env['res.partner'].create({'name': 'Recompute Archived', 'active': False})
        cls.manager = new_test_user(cls.env, login='recompute_manager', groups='base.group_user,base.group_erp_manager')

    def _corrupt(self, partners):
        partners.flush_recordset()
        self.env.cr.execute("UPDATE res_partner SET complete_name = 'corrupted' WHERE id IN %s", [tuple(partners.ids)])
        partners.invalidate_recordset(['complete_name'])

    def test_can_recompute(self):
        self.assertTrue(self.complete_name.can_recompute)
        self.assertFalse(self.partner_name.can_recompute)
        # non-stored computed field
        self.assertFalse(self.Fields._get('res.partner', 'display_name').can_recompute)

    def test_recompute_restores_values_including_archived(self):
        partners = self.partner | self.archived
        self._corrupt(partners)
        self.assertEqual(partners.with_context(active_test=False).mapped('complete_name'), ['corrupted', 'corrupted'])
        self.complete_name.recompute_field()
        partners.invalidate_recordset(['complete_name'])
        self.assertEqual(self.partner.complete_name, 'Recompute Active')
        self.assertEqual(self.archived.complete_name, 'Recompute Archived')

    def test_recompute_non_computed_field_raises(self):
        with self.assertRaises(UserError):
            self.partner_name.recompute_field()

    def test_recompute_requires_system_group(self):
        # an access-rights manager can read/write ir.model.fields but must not
        # be able to trigger a full recompute through RPC
        with self.assertRaises(AccessError):
            self.complete_name.with_user(self.manager).recompute_field()

    def test_form_view_renders_for_admin(self):
        arch = self.Fields.get_view(view_type='form')['arch']
        self.assertIn('recompute_field', arch)
        arch = self.Fields.with_user(self.manager).get_view(view_type='form')['arch']
        self.assertNotIn('recompute_field', arch)
