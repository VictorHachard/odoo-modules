from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from ..model.cv_ir_cron_history import CRON_BUS_CHANNEL
from ..model.ir_websocket import IrWebsocket as CvIrWebsocket
from .common import CronHistoryCase


class _FakeRequest:
    """The bits of `odoo.http.request` the bus channel chain reads."""

    def __init__(self, uid):
        self.session = type('Session', (), {'uid': uid})()


@tagged('post_install', '-at_install')
class TestCronAccess(CronHistoryCase):
    """Who may read the history, and who may listen to the dashboard channel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = new_test_user(cls.env, login='cv_employee', password='Cv-Employee-2026!', groups='base.group_user')
        cls.erp_manager = new_test_user(cls.env, login='cv_erp_manager', password='Cv-Manager-2026!',
                                        groups='base.group_user,base.group_erp_manager')
        cls.admin = new_test_user(cls.env, login='cv_admin', password='Cv-Admin-2026!', groups='base.group_user,base.group_system')
        cls.portal = new_test_user(cls.env, login='cv_portal', password='Cv-Portal-2026!', groups='base.group_portal')
        cls.public = cls.env.ref('base.public_user')

    # ------------------------------------------------------------------
    # Model access
    # ------------------------------------------------------------------

    def test_history_is_readable_by_settings_users(self):
        row = self._run()
        self.assertEqual(self.History.with_user(self.admin).search([('id', '=', row.id)]), row)

    def test_history_is_hidden_from_everyone_else(self):
        self._run()
        for user in (self.employee, self.erp_manager, self.portal, self.public):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                self.History.with_user(user).search([])

    def test_history_cannot_be_forged_by_employees(self):
        row = self._run()
        History = self.History.with_user(self.employee)
        with self.assertRaises(AccessError):
            History.create({'ir_cron_id': self.cron.id})
        with self.assertRaises(AccessError):
            row.with_user(self.employee).write({'state': 'success'})
        with self.assertRaises(AccessError):
            row.with_user(self.employee).unlink()

    def test_employees_cannot_trigger_crons(self):
        with self.assertRaises(AccessError):
            self.cron.with_user(self.employee).method_direct_trigger()

    def test_employees_cannot_read_the_dashboard_fields(self):
        for user in (self.employee, self.portal):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                self.cron.with_user(user).read(['cv_history', 'cv_is_running'])

    def test_settings_users_read_the_dashboard_fields(self):
        self._run()
        values = self.cron.with_user(self.admin).read(
            ['cv_history', 'cv_is_running', 'cv_progress_estimated', 'cv_history_count', 'cv_next_execution_timer'])
        self.assertEqual(values[0]['cv_history_count'], 1)

    def test_kanban_view_and_action_are_reachable_by_settings_users(self):
        kanban = self.env.ref('cron_visualization.cv_ir_cron_kanban_view')
        self.env['ir.cron'].with_user(self.admin).get_views([(kanban.id, 'kanban')])

    # ------------------------------------------------------------------
    # Dashboard bus channel
    # ------------------------------------------------------------------

    def _channels_after_filter(self, user, channels):
        """Run only this module's override, with the rest of the chain stubbed out."""
        websocket = self.env['ir.websocket'].with_user(user)
        mro = type(websocket).__mro__
        next_cls = mro[mro.index(CvIrWebsocket) + 1]
        with patch.object(next_cls, '_build_bus_channel_list', lambda self, ch: ch, create=True):
            return CvIrWebsocket._build_bus_channel_list(websocket, list(channels))

    @staticmethod
    def _strings(channels):
        return [c for c in channels if isinstance(c, str)]

    def _subscribed(self, user, channels):
        """The channel set a websocket of `user` really subscribes to."""
        with patch('odoo.addons.bus.models.ir_websocket.request', _FakeRequest(user.id if not user._is_public() else None)):
            data = self.env['ir.websocket'].with_user(user)._prepare_subscribe_data(list(channels), 0)
        return data['channels']

    def test_dashboard_channel_kept_for_settings_users(self):
        channels = self._channels_after_filter(self.admin, [CRON_BUS_CHANNEL, 'other'])
        self.assertIn(CRON_BUS_CHANNEL, channels)
        self.assertIn('other', channels)

    def test_dashboard_channel_kept_for_the_admin_user(self):
        channels = self._channels_after_filter(self.env.ref('base.user_admin'), [CRON_BUS_CHANNEL])
        self.assertIn(CRON_BUS_CHANNEL, channels)

    def test_dashboard_channel_stripped_for_non_settings_users(self):
        for user in (self.employee, self.erp_manager, self.portal, self.public):
            with self.subTest(user=user.login):
                partner = user.partner_id
                channels = self._channels_after_filter(user, [CRON_BUS_CHANNEL, 'other', partner])
                self.assertNotIn(CRON_BUS_CHANNEL, self._strings(channels))
                self.assertIn('other', self._strings(channels))
                self.assertIn(partner, [c for c in channels if not isinstance(c, str)])

    def test_channel_list_without_the_dashboard_is_untouched(self):
        partner = self.employee.partner_id
        channels = self._channels_after_filter(self.employee, ['other', partner])
        self.assertEqual(channels, ['other', partner])

    def test_duplicated_dashboard_channel_is_fully_stripped(self):
        channels = self._channels_after_filter(self.employee, [CRON_BUS_CHANNEL, CRON_BUS_CHANNEL])
        self.assertEqual(channels, [])

    def test_lookalike_channels_are_untouched(self):
        lookalikes = [CRON_BUS_CHANNEL + 'x', CRON_BUS_CHANNEL.upper()]
        channels = self._channels_after_filter(self.employee, lookalikes)
        self.assertEqual(channels, lookalikes)

    def test_websocket_subscription_of_a_settings_user(self):
        """End to end, through `_prepare_subscribe_data` as the websocket runs it."""
        subscribed = self._subscribed(self.admin, [CRON_BUS_CHANNEL])
        self.assertIn(CRON_BUS_CHANNEL, subscribed)

    def test_websocket_subscription_of_other_users(self):
        for user in (self.employee, self.erp_manager, self.portal, self.public):
            with self.subTest(user=user.login):
                subscribed = self._subscribed(user, [CRON_BUS_CHANNEL, 'other'])
                self.assertNotIn(CRON_BUS_CHANNEL, self._strings(subscribed))
                self.assertIn('other', self._strings(subscribed))

    def test_settings_group_channel_is_not_the_dashboard_channel(self):
        """Settings users are subscribed to their group channel on every page;
        the dashboard notifications must not travel on it."""
        subscribed = self._subscribed(self.admin, [])
        self.assertNotIn(CRON_BUS_CHANNEL, self._strings(subscribed))
        self.assertIn(self.env.ref('base.group_system'), [c for c in subscribed if not isinstance(c, str)])

    def test_dashboard_notification_targets_only_the_dashboard_channel(self):
        targets = []
        BusBus = type(self.env['bus.bus'])
        with patch.object(BusBus, '_sendone', lambda bus, target, *a: targets.append(target)):
            self._run()
        self.assertTrue(targets)
        self.assertEqual(set(targets), {CRON_BUS_CHANNEL})
