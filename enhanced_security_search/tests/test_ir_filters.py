# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo import Command
from odoo.addons.enhanced_security_search import _post_init
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

GROUP = 'enhanced_security_search.group_custom_search'


class IrFiltersCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_custom_search = cls.env.ref(GROUP)
        group_user = cls.env.ref('base.group_user')

        # User WITH the group: allowed.
        cls.user_allowed = cls.env['res.users'].create({
            'name': 'Allowed',
            'login': 'allowed@example.com',
            'group_ids': [Command.set([group_user.id, cls.group_custom_search.id])],
        })
        # User WITHOUT the group: blocked.
        cls.user_blocked = cls.env['res.users'].create({
            'name': 'Blocked',
            'login': 'blocked@example.com',
            'group_ids': [Command.set([group_user.id])],
        })
        cls.user_blocked.group_ids -= cls.group_custom_search
        # Another user with the group, to share filters with.
        cls.user_colleague = cls.env['res.users'].create({
            'name': 'Colleague',
            'login': 'colleague@example.com',
            'group_ids': [Command.set([group_user.id, cls.group_custom_search.id])],
        })
        # Administrators, deliberately outside the group.
        cls.user_erp_manager = cls.env['res.users'].create({
            'name': 'ERP Manager',
            'login': 'erp_manager@example.com',
            'group_ids': [Command.set([group_user.id, cls.env.ref('base.group_erp_manager').id])],
        })
        cls.user_erp_manager.group_ids -= cls.group_custom_search
        cls.user_system = cls.env['res.users'].create({
            'name': 'System',
            'login': 'system@example.com',
            'group_ids': [Command.set([group_user.id, cls.env.ref('base.group_system').id])],
        })
        cls.user_system.group_ids -= cls.group_custom_search
        cls.user_portal = new_test_user(cls.env, login='ess_portal', groups='base.group_portal')
        cls.user_public = cls.env.ref('base.public_user')

    def _vals(self, name='My Filter', **extra):
        return {
            'name': name,
            'model_id': 'res.partner',
            'domain': '[]',
            'context': '{}',
            **extra,
        }

    def _filter(self, name='Filter', owner=None, users=None):
        """A filter created by `owner` (admin when omitted), shared with
        `users` (a private filter of `owner` when omitted; pass an empty
        recordset to share it with everyone)."""
        Filters = self.env['ir.filters'].with_user(owner) if owner else self.env['ir.filters'].sudo()
        if users is None:
            users = owner or self.env.user
        return Filters.create(self._vals(name, user_ids=[Command.set(users.ids)]))


@tagged('post_install', '-at_install')
class TestIrFiltersAccess(IrFiltersCase):
    """`ir.filters` create/write/unlink are gated by the custom-search group.
    The JS hide is UI only; the server-side gate is the real fence."""

    # ------------------------------------------------------------------
    # Group membership: create / write / unlink
    # ------------------------------------------------------------------

    def test_allowed_user_can_create_filter(self):
        filt = self.env['ir.filters'].with_user(self.user_allowed).create(self._vals('Allowed Create'))
        self.assertTrue(filt.exists())

    def test_allowed_user_can_use_create_filter(self):
        """The RPC the "Save current search" button really calls."""
        filt = self.env['ir.filters'].with_user(self.user_allowed).create_filter(
            self._vals('Saved Search', user_ids=[self.user_allowed.id]))
        self.assertEqual(filt.user_ids, self.user_allowed)

    def test_allowed_user_can_write_filter(self):
        filt = self.env['ir.filters'].with_user(self.user_allowed).create(self._vals('Will Be Renamed'))
        filt.with_user(self.user_allowed).write({'name': 'Renamed'})
        self.assertEqual(filt.name, 'Renamed')

    def test_allowed_user_can_unlink_filter(self):
        filt = self.env['ir.filters'].with_user(self.user_allowed).create(self._vals('Will Be Deleted'))
        filt.with_user(self.user_allowed).unlink()
        self.assertFalse(filt.exists())

    def test_blocked_user_cannot_create_filter(self):
        with self.assertRaises(AccessError):
            self.env['ir.filters'].with_user(self.user_blocked).create(self._vals('Blocked Create'))

    def test_blocked_user_cannot_use_create_filter(self):
        with self.assertRaises(AccessError):
            self.env['ir.filters'].with_user(self.user_blocked).create_filter(
                self._vals('Blocked Save', user_ids=[self.user_blocked.id]))

    def test_blocked_user_cannot_create_a_batch(self):
        with self.assertRaises(AccessError):
            self.env['ir.filters'].with_user(self.user_blocked).create([self._vals('A'), self._vals('B')])

    def test_blocked_user_cannot_write_their_own_filter(self):
        own = self._filter('Own Before Removal', users=self.user_blocked)
        with self.assertRaises(AccessError):
            own.with_user(self.user_blocked).write({'name': 'Hijacked'})

    def test_blocked_user_cannot_write_filter(self):
        filt = self.env['ir.filters'].create(self._vals('Existing'))
        with self.assertRaises(AccessError):
            filt.with_user(self.user_blocked).write({'name': 'Hijacked'})

    def test_blocked_user_cannot_unlink_filter(self):
        filt = self.env['ir.filters'].create(self._vals('Existing 2'))
        with self.assertRaises(AccessError):
            filt.with_user(self.user_blocked).unlink()

    def test_blocked_user_can_still_read_and_apply_filters(self):
        """Reading is not gated: predefined favourites keep working."""
        shared = self._filter('Shared For All', users=self.env['res.users'])
        found = self.env['ir.filters'].with_user(self.user_blocked).get_filters('res.partner')
        self.assertIn(shared.id, [f['id'] for f in found])
        self.assertEqual(shared.with_user(self.user_blocked).name, 'Shared For All')

    def test_blocked_user_empty_write_and_unlink_are_still_refused(self):
        """The group check does not depend on the recordset content."""
        Filters = self.env['ir.filters'].with_user(self.user_blocked)
        with self.assertRaises(AccessError):
            Filters.browse().write({'name': 'x'})
        with self.assertRaises(AccessError):
            Filters.browse().unlink()

    def test_losing_the_group_takes_effect_immediately(self):
        Filters = self.env['ir.filters'].with_user(self.user_colleague)
        Filters.create(self._vals('Before'))
        self.user_colleague.group_ids -= self.group_custom_search
        with self.assertRaises(AccessError):
            Filters.create(self._vals('After'))

    # ------------------------------------------------------------------
    # Bypass: superuser and administrators
    # ------------------------------------------------------------------

    def test_superuser_bypass(self):
        """sudo() always bypasses the check (otherwise the post_init hook,
        cron jobs and internal automations would all break)."""
        filt = self.env['ir.filters'].sudo().create(self._vals('Sudo OK'))
        self.assertTrue(filt.exists())
        filt.sudo().write({'name': 'Sudo Renamed'})
        filt.sudo().unlink()
        self.assertFalse(filt.exists())

    def test_sudo_from_a_blocked_user_bypasses(self):
        """Server code acting on behalf of a blocked user with sudo()."""
        filt = self.env['ir.filters'].with_user(self.user_blocked).sudo().create(
            self._vals('Sudo Blocked', user_ids=[Command.set(self.user_blocked.ids)]))
        filt.with_user(self.user_blocked).sudo().write({'name': 'Sudo Blocked Renamed'})
        filt.with_user(self.user_blocked).sudo().unlink()
        self.assertFalse(filt.exists())

    def test_admin_bypass(self):
        """`_is_admin()` users (group_erp_manager, and group_system that implies
        it) bypass too, group or not."""
        for admin in (self.user_erp_manager, self.user_system):
            with self.subTest(admin=admin.login):
                self.assertFalse(admin.has_group(GROUP))
                Filters = self.env['ir.filters'].with_user(admin)
                filt = Filters.create(self._vals('Admin Create'))
                self.assertTrue(filt.exists())
                shared = self._filter('Somebody Else Shared', owner=self.user_allowed, users=self.env['res.users'])
                shared.with_user(admin).write({'name': 'Admin Renamed'})
                shared.with_user(admin).unlink()
                self.assertFalse(shared.exists())

    # ------------------------------------------------------------------
    # Portal and public users
    # ------------------------------------------------------------------

    def test_portal_user_cannot_manage_filters(self):
        self.assertFalse(self.user_portal.has_group(GROUP))
        with self.assertRaises(AccessError):
            self.env['ir.filters'].with_user(self.user_portal).create(
                self._vals('Portal', user_ids=[Command.set(self.user_portal.ids)]))
        own = self._filter('Portal Own', users=self.user_portal)
        with self.assertRaises(AccessError):
            own.with_user(self.user_portal).write({'name': 'Portal Renamed'})
        with self.assertRaises(AccessError):
            own.with_user(self.user_portal).unlink()

    def test_public_user_cannot_manage_filters(self):
        with self.assertRaises(AccessError):
            self.env['ir.filters'].with_user(self.user_public).create(self._vals('Public'))
        shared = self._filter('Shared With Public', users=self.env['res.users'])
        with self.assertRaises(AccessError):
            shared.with_user(self.user_public).unlink()

    # ------------------------------------------------------------------
    # Shared filters
    # ------------------------------------------------------------------

    def test_user_cannot_touch_someone_elses_shared_filter(self):
        """A filter with no user is instance-wide: only its author or an
        administrator may change or delete it."""
        shared = self.env['ir.filters'].create(self._vals('Shared By Admin'))
        self.assertFalse(shared.user_ids)
        with self.assertRaises(AccessError):
            shared.with_user(self.user_allowed).write({'domain': "[('id', '>', 0)]"})
        with self.assertRaises(AccessError):
            shared.with_user(self.user_allowed).unlink()
        self.assertEqual(shared.domain, '[]')

    def test_user_cannot_touch_a_filter_shared_with_several_users(self):
        """Shared with a list of users, the author's colleague is in that list
        and core's rule lets them write: this module does not."""
        shared = self._filter('Team Filter', owner=self.user_colleague,
                              users=self.user_colleague | self.user_allowed)
        with self.assertRaises(AccessError):
            shared.with_user(self.user_allowed).write({'name': 'Mine Now'})
        with self.assertRaises(AccessError):
            shared.with_user(self.user_allowed).write({'user_ids': [Command.set(self.user_allowed.ids)]})
        with self.assertRaises(AccessError):
            shared.with_user(self.user_allowed).unlink()

    def test_user_can_still_manage_the_shared_filter_they_created(self):
        """Sharing a favourite stays a feature: its author keeps full control."""
        shared = self.env['ir.filters'].with_user(self.user_allowed).create(self._vals('Shared By Me'))
        shared.with_user(self.user_allowed).write({'name': 'Shared By Me, Renamed'})
        shared.with_user(self.user_allowed).unlink()
        self.assertFalse(shared.exists())

    def test_author_can_share_and_unshare(self):
        filt = self._filter('Private Then Shared', owner=self.user_allowed)
        filt.with_user(self.user_allowed).write({'user_ids': [Command.set((self.user_allowed | self.user_colleague).ids)]})
        filt.with_user(self.user_allowed).write({'user_ids': [Command.clear()]})
        self.assertFalse(filt.user_ids)
        filt.with_user(self.user_allowed).write({'user_ids': [Command.set(self.user_allowed.ids)]})
        self.assertEqual(filt.user_ids, self.user_allowed)

    def test_author_can_create_a_shared_filter_with_a_context(self):
        """core sanitises the context of a shared filter with a write on create."""
        filt = self.env['ir.filters'].with_user(self.user_allowed).create(
            self._vals('Shared With Context', context="{'default_name': 'x', 'group_by': ['name']}"))
        self.assertNotIn('default_name', filt.context)

    def test_private_filter_made_for_a_user_stays_theirs(self):
        """A private filter is the user's even when an administrator made it."""
        filt = self._filter('Made For You', users=self.user_allowed)
        filt.with_user(self.user_allowed).write({'name': 'Mine'})
        filt.with_user(self.user_allowed).unlink()
        self.assertFalse(filt.exists())

    def test_mixed_recordset_is_refused_as_a_whole(self):
        own = self._filter('Own', owner=self.user_allowed)
        foreign = self._filter('Foreign Shared', users=self.env['res.users'])
        with self.assertRaises(AccessError):
            (own | foreign).with_user(self.user_allowed).unlink()
        self.assertTrue(own.exists())
        self.assertTrue(foreign.exists())

    def test_others_private_filters_stay_out_of_reach(self):
        """Core's record rule, which this module keeps."""
        private = self._filter('Colleague Private', owner=self.user_colleague)
        with self.assertRaises(AccessError):
            private.with_user(self.user_allowed).write({'name': 'Peek'})


@tagged('post_install', '-at_install')
class TestCustomSearchGroup(IrFiltersCase):
    """Who holds the group: the post_init hook, the default user template,
    and what the web client is told."""

    def test_post_init_grants_group_to_internal_users(self):
        """The post_init hook grants the group to every existing internal user."""
        self.assertNotIn(self.group_custom_search, self.user_blocked.group_ids)
        _post_init(self.env)
        self.user_blocked.invalidate_recordset(['group_ids'])
        self.assertIn(self.group_custom_search, self.user_blocked.group_ids)

    def test_post_init_includes_archived_internal_users(self):
        self.user_blocked.active = False
        _post_init(self.env)
        self.assertTrue(self.user_blocked.with_context(active_test=False).has_group(GROUP))

    def test_post_init_leaves_portal_and_public_users_alone(self):
        _post_init(self.env)
        self.assertFalse(self.user_portal.has_group(GROUP))
        self.assertFalse(self.user_public.has_group(GROUP))

    def test_post_init_is_idempotent(self):
        _post_init(self.env)
        members = self.group_custom_search.with_context(active_test=False).user_ids
        _post_init(self.env)
        self.assertEqual(self.group_custom_search.with_context(active_test=False).user_ids, members)

    def test_post_init_with_no_internal_user(self):
        with patch.object(type(self.env['res.users']), 'search', lambda *a, **k: self.env['res.users']):
            _post_init(self.env)

    def test_new_internal_user_gets_the_group_by_default(self):
        """A user created without an explicit `group_ids` picks the group up
        from `base.default_user_group`, so the population is the same for users
        created before and after the install."""
        new_internal = self.env['res.users'].create({
            'name': 'New Internal',
            'login': 'new_internal@example.com',
        })
        self.assertIn(self.group_custom_search, new_internal.group_ids)
        # And it is a plain membership, so it can be taken away from one user.
        new_internal.group_ids -= self.group_custom_search
        self.assertFalse(new_internal.has_group(GROUP))

    def test_new_portal_user_does_not_get_the_group(self):
        portal = self.env['res.users'].create({
            'name': 'New Portal',
            'login': 'new_portal@example.com',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })
        self.assertFalse(portal.has_group(GROUP))

    def test_group_is_linked_to_the_default_user_template(self):
        self.assertIn(self.env.ref('base.default_user_group'), self.group_custom_search.implied_by_ids)
        self.assertEqual(self.group_custom_search.privilege_id,
                         self.env.ref('enhanced_security_search.res_groups_privilege_website'))


@tagged('post_install', '-at_install')
class TestCustomSearchSessionInfo(HttpCase):
    """The group is answered from the page, so the search bar never asks."""

    def _session_info(self, login):
        # Created lazily by core on the first session_info, which runs on a
        # read-only cursor and logs an error before retrying: create it first.
        user = self.env['res.users'].search([('login', '=', login)])
        self.env['res.users.settings'].sudo()._find_or_create_for_user(user)
        self.authenticate(login, login)
        return self.make_jsonrpc_request('/web/session/get_session_info')

    def test_session_info_tells_the_client(self):
        group = self.env.ref(GROUP)
        allowed = new_test_user(self.env, login='ess_http_allowed', groups='base.group_user')
        blocked = new_test_user(self.env, login='ess_http_blocked', groups='base.group_user')
        allowed.group_ids |= group
        blocked.group_ids -= group
        self.assertIs(self._session_info(allowed.login)['groups'][GROUP], True)
        self.assertIs(self._session_info(blocked.login)['groups'][GROUP], False)

    def test_session_info_for_portal_users(self):
        """Portal users have no back office: nothing is added for them."""
        portal = new_test_user(self.env, login='ess_http_portal', groups='base.group_portal')
        self.assertNotIn(GROUP, self._session_info(portal.login).get('groups', {}))
