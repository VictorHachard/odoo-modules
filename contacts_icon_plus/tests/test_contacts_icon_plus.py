# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

GROUP = 'contacts_icon_plus.group_partner_icon_type_detailed'


@tagged('post_install', '-at_install')
class TestPartnerIconType(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.company = Partner.create({'name': 'Icon Company', 'vat': 'BE0477472701'})
        cls.individual = Partner.create({'name': 'Icon Individual'})
        cls.employee = Partner.create({'name': 'Icon Employee', 'parent_id': cls.company.id})
        cls.contact = Partner.create({'name': 'Icon Contact', 'parent_id': cls.individual.id})

    def assertIconTypes(self, partner, detailed, easy):
        self.assertEqual((partner.icon_type_selection, partner.icon_type_selection_easy), (detailed, easy), partner.name)

    def test_compute_types(self):
        self.assertIconTypes(self.company, 'company', 'company')
        self.assertIconTypes(self.individual, 'individual', 'individual')
        self.assertIconTypes(self.employee, 'employee', 'employee')
        self.assertIconTypes(self.contact, 'contact', 'contact')
        for address_type in ('invoice', 'delivery', 'other'):
            address = self.env['res.partner'].create({
                'name': f'Icon {address_type}', 'parent_id': self.company.id, 'type': address_type,
            })
            self.assertIconTypes(address, address_type, 'contact')

    def test_selection_matches_partner_address_types(self):
        partner_types = {value for value, _label in self.env['res.partner']._fields['type'].selection}
        icon_types = {value for value, _label in self.env['res.partner']._fields['icon_type_selection'].selection}
        self.assertLessEqual(partner_types - {'contact'}, icon_types)

    def test_recompute_on_change(self):
        # Odoo 20 derives is_company from the VAT of a commercial entity
        self.individual.vat = 'BE0477472701'
        self.assertIconTypes(self.individual, 'company', 'company')
        self.assertIconTypes(self.contact, 'employee', 'employee')
        self.employee.type = 'delivery'
        self.assertIconTypes(self.employee, 'delivery', 'contact')
        self.contact.write({'parent_id': False, 'type': 'contact', 'vat': False})
        self.assertIconTypes(self.contact, 'individual', 'individual')

    def test_search_filters(self):
        Partner = self.env['res.partner']
        self.assertIn(self.employee, Partner.search([('icon_type_selection', '=', 'employee')]))
        self.assertNotIn(self.individual, Partner.search([('icon_type_selection', '=', 'employee')]))
        arch = Partner.get_view(view_type='search')['arch']
        for name in ('type_individual', 'type_company', 'type_employee', 'type_contact', 'group_icon_type_selection_easy'):
            self.assertIn(f'name="{name}"', arch)
        self.assertEqual(arch.count('name="type_company"'), 1)


@tagged('post_install', '-at_install')
class TestPartnerIconPreference(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env.ref(GROUP)
        cls.user = new_test_user(cls.env, login='icon_user', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, login='icon_other', groups='base.group_user')

    def test_user_toggles_own_preference(self):
        user = self.user.with_user(self.user)
        self.assertFalse(user.partner_icon_type_detailed)
        user.write({'partner_icon_type_detailed': True})
        self.assertIn(self.group, self.user.group_ids)
        self.assertTrue(self.user.partner_icon_type_detailed)
        user.write({'partner_icon_type_detailed': False})
        self.assertNotIn(self.group, self.user.group_ids)
        self.assertFalse(self.user.partner_icon_type_detailed)

    def test_user_cannot_toggle_other_user(self):
        with self.assertRaises(AccessError):
            self.other_user.with_user(self.user).write({'partner_icon_type_detailed': True})
        self.assertNotIn(self.group, self.other_user.group_ids)

    def test_preference_follows_group_membership(self):
        """ The flag used to be a stored boolean that drifted from the group. """
        self.user.group_ids = [(4, self.group.id)]
        self.assertTrue(self.user.partner_icon_type_detailed)
        self.group.user_ids = [(3, self.user.id)]
        self.user.invalidate_recordset()
        self.assertFalse(self.user.partner_icon_type_detailed)

    def test_create_user_with_preference(self):
        """ create() used to crash when group_ids was not in the values. """
        user = self.env['res.users'].create({
            'name': 'Icon New', 'login': 'icon_new', 'partner_icon_type_detailed': True,
        })
        self.assertIn(self.group, user.group_ids)
        self.assertIn(self.env.ref('base.group_user'), user.all_group_ids)

    def test_views_depend_on_preference(self):
        Partner = self.env['res.partner'].with_user(self.user)
        arch = Partner.get_view(view_type='list')['arch']
        self.assertIn('widget="partner_icon_type"', arch)
        self.assertNotIn('partner_icon_type_all', arch)
        self.user.partner_icon_type_detailed = True
        self.env.invalidate_all()
        arch = Partner.get_view(view_type='list')['arch']
        self.assertIn('partner_icon_type_all', arch)
        kanban = Partner.get_view(view_type='kanban')['arch']
        self.assertIn('partner_icon_type_all', kanban)
        prefs = self.env['res.users'].with_user(self.user).get_view(
            self.env.ref('base.view_users_form_simple_modif').id, 'form')['arch']
        self.assertIn('partner_icon_type_detailed', prefs)


@tagged('post_install', '-at_install')
class TestPartnerIconUi(HttpCase):

    def test_contacts_list_renders_icons(self):
        self.env['res.partner'].create({'name': 'Icon UI Company', 'vat': 'BE0477472701'})
        code = """
            (async () => {
                const deadline = Date.now() + 30000;
                while (!document.querySelector('.o_list_view .o_partner_icon_type i.fa-building')) {
                    if (Date.now() > deadline) {
                        console.error('partner icon not rendered');
                        return;
                    }
                    await new Promise((resolve) => setTimeout(resolve, 100));
                }
                console.log('test successful');
            })();
        """
        self.browser_js('/odoo/action-contacts.action_contacts?view_type=list', code, login='admin', timeout=90)

