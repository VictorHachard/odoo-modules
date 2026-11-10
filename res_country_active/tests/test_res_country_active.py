# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestResCountryActive(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Country = cls.env['res.country']
        cls.belgium = cls.env.ref('base.be')

    def test_countries_active_by_default(self):
        self.assertTrue(self.belgium.active)
        self.assertFalse(self.Country.search([('active', '=', False)]))

    def test_archive_hides_country_from_search(self):
        self.belgium.action_archive()
        self.assertNotIn(self.belgium, self.Country.search([]))
        self.assertNotIn(self.belgium.id, [cid for cid, _name in self.Country.name_search('Belgium')])
        self.assertIn(self.belgium, self.Country.with_context(active_test=False).search([]))
        self.belgium.action_unarchive()
        self.assertIn(self.belgium, self.Country.search([]))

    def test_archived_country_kept_on_partners(self):
        partner = self.env['res.partner'].create({'name': 'Belgian partner', 'country_id': self.belgium.id})
        self.belgium.action_archive()
        partner.invalidate_recordset()
        self.assertEqual(partner.country_id, self.belgium)
        self.assertEqual(partner.country_code, 'BE')

    def test_cached_data_still_lists_archived_country(self):
        self.belgium.action_archive()
        self.assertIn(self.belgium, self.Country.get_all())
        self.assertEqual(self.Country._phone_code_for('BE'), 32)

    def test_views(self):
        search_arch = self.Country.get_view(view_type='search')['arch']
        self.assertIn('name="inactive"', search_arch)
        list_arch = self.Country.get_view(view_type='list')['arch']
        self.assertIn('name="active"', list_arch)
