from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from ..model import ir_cron as cv_ir_cron
from .common import CronHistoryCase


@tagged('post_install', '-at_install')
class TestCronCallback(CronHistoryCase):
    """The _callback wrapper that records every run, manual or automatic."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model = cls.env['ir.model']._get('res.partner')
        cls.failing_cron = cls._make_cron('CV failing cron', model, code="raise UserError('lamp broken')")

    def setUp(self):
        super().setUp()
        for attr in ('key', 'history_id'):
            if hasattr(cv_ir_cron._cron_run, attr):
                delattr(cv_ir_cron._cron_run, attr)
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.commits = []
        stack.enter_context(patch.object(self.env.cr, 'commit', lambda: self.commits.append('commit')))
        stack.enter_context(patch.object(self.env.cr, 'rollback', lambda: self.commits.append('rollback')))

    def _call(self, cron, **context):
        cron = cron.with_context(**context) if context else cron
        cron._callback(cron.name, cron.ir_actions_server_id.id)

    def _raising(self, exception, cron, **context):
        try:
            self._call(cron, **context)
        except exception:
            return
        self.fail('%s was not raised' % exception.__name__)

    def _rows(self, cron=None):
        return self.History.search([('ir_cron_id', '=', (cron or self.cron).id)])

    def test_automatic_run_is_recorded_as_success(self):
        self._call(self.cron)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(row.type, 'automatic')
        self.assertEqual(row.user_id, self.env.user)
        self.assertTrue(row.ended_at)
        self.assertGreaterEqual(row.duration, 0)

    def test_running_row_is_committed_before_the_action(self):
        seen = []
        Server = type(self.env['ir.actions.server'])
        original = Server.run

        def spy(action):
            seen.append((self._rows().state, list(self.commits)))
            return original(action)

        with patch.object(Server, 'run', spy):
            self._call(self.cron)
        self.assertEqual(seen[0][0], 'running')
        self.assertEqual(seen[0][1], ['commit'])

    def test_failing_run_is_recorded_and_the_error_propagates(self):
        try:
            self._call(self.failing_cron)
        except UserError:
            pass
        else:
            self.fail('the cron error was swallowed')
        row = self._rows(self.failing_cron)
        self.assertEqual(row.state, 'fail')
        self.assertIn('lamp broken', row.error)
        self.assertTrue(row.ended_at)
        self.assertEqual(self.commits[-1], 'commit')

    def test_manual_run_records_the_operator(self):
        operator = new_test_user(self.env, login='cv_operator', password='Cv-Operator-2026!',
                                 groups='base.group_user,base.group_system')
        fake_request = MagicMock()
        fake_request.env.user.id = operator.id
        with patch.object(cv_ir_cron, 'request', fake_request):
            self._call(self.cron)
        row = self._rows()
        self.assertEqual(row.type, 'manual')
        self.assertEqual(row.user_id, operator)

    def test_progress_iterations_share_one_row(self):
        states_during_run = []
        Server = type(self.env['ir.actions.server'])
        original = Server.run

        def spy(action):
            states_during_run.append(self._rows().state)
            return original(action)

        context = {'cron_id': self.cron.id, 'cron_end_time': 12345.0}
        with patch.object(Server, 'run', spy):
            self._call(self.cron, **context)
            self._call(self.cron, **context)
            self._call(self.cron, **context)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(states_during_run, ['running'] * 3)

    def test_a_new_run_gets_a_new_row(self):
        self._call(self.cron, cron_id=self.cron.id, cron_end_time=1.0)
        self._call(self.cron, cron_id=self.cron.id, cron_end_time=2.0)
        self.assertEqual(len(self._rows()), 2)

    def test_runs_without_end_time_never_share_a_row(self):
        self._call(self.cron)
        self._call(self.cron)
        self.assertEqual(len(self._rows()), 2)

    def test_deleted_row_between_iterations_is_recreated(self):
        context = {'cron_id': self.cron.id, 'cron_end_time': 99.0}
        self._call(self.cron, **context)
        self._rows().unlink()
        self._call(self.cron, **context)
        self.assertEqual(len(self._rows()), 1)
        self.assertEqual(self._rows().state, 'success')

    def test_callback_notifies_the_dashboard(self):
        with self._capture_bus() as sent:
            self._call(self.cron)
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(payload['cron_ids'] == [self.cron.id] for _t, payload in sent))

    def test_success_commit_sequence(self):
        """running row committed, then the action (core commits), then the closing."""
        self._call(self.cron)
        self.assertEqual(self.commits, ['commit', 'commit', 'commit'])

    def test_failure_commit_sequence(self):
        with self.assertRaises(UserError):
            self._call(self.failing_cron)
        self.assertEqual(self.commits, ['commit', 'rollback', 'commit'])

    def test_error_without_message_records_the_exception(self):
        Server = type(self.env['ir.actions.server'])

        def boom(action):
            raise RuntimeError()

        # Not assertRaises: Odoo's rolls a savepoint back, history row included.
        with patch.object(Server, 'run', boom):
            self._raising(RuntimeError, self.cron)
        self.assertEqual(self._rows().error, 'RuntimeError()')

    def test_failed_iteration_then_success_in_the_same_run(self):
        """A progress-API run may fail one batch and go on with the next one."""
        Server = type(self.env['ir.actions.server'])
        original = Server.run
        calls = []

        def flaky(action):
            calls.append(1)
            if len(calls) == 1:
                raise UserError('first batch broke')
            return original(action)

        context = {'cron_id': self.cron.id, 'cron_end_time': 4242.0}
        with patch.object(Server, 'run', flaky):
            self._raising(UserError, self.cron, **context)
            self.assertEqual(self._rows().state, 'fail')
            self._call(self.cron, **context)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertTrue(row.ended_at)

    def test_thread_slot_is_per_database(self):
        """A cron thread serves every database; the same cron id and end time
        in another database must not reuse this database's row."""
        first = self._run(state='success')
        cv_ir_cron._cron_run.key = ('some_other_db', self.cron.id, 5.0)
        cv_ir_cron._cron_run.history_id = first.id
        self._call(self.cron, cron_id=self.cron.id, cron_end_time=5.0)
        self.assertEqual(len(self._rows()), 2)
        self.assertEqual(first.state, 'success')

    def test_thread_slot_pointing_to_another_cron_is_not_reused(self):
        foreign = self._run(cron=self.other_cron, state='success')
        cv_ir_cron._cron_run.key = (self.env.cr.dbname, self.cron.id, 6.0)
        cv_ir_cron._cron_run.history_id = foreign.id
        self._call(self.cron, cron_id=self.cron.id, cron_end_time=6.0)
        self.assertEqual(len(self._rows()), 1)
        self.assertEqual(foreign.state, 'success')
        self.assertEqual(self._rows(self.other_cron), foreign)

    def test_history_row_is_created_as_superuser_for_the_scheduler_user(self):
        """`_run_job` runs the action as the cron's user, who needs no access
        to the history model for the row to be written."""
        employee = new_test_user(self.env, login='cv_cron_runner', password='Cv-Runner-2026!',
                                 groups='base.group_user')
        Server = type(self.env['ir.actions.server'])
        with patch.object(Server, 'run', lambda action: None):
            self.cron.with_user(employee)._callback(self.cron.name, self.cron.ir_actions_server_id.id)
        row = self._rows()
        self.assertEqual(row.user_id, employee)
        self.assertEqual(row.state, 'success')

    def test_run_manually_records_the_run(self):
        """The real "Run Manually" path, through `_process_job` and `_run_job`."""
        operator = new_test_user(self.env, login='cv_operator2', password='Cv-Operator-2026!',
                                 groups='base.group_user,base.group_system')
        fake_request = MagicMock()
        fake_request.env.user.id = operator.id
        with self.enter_registry_test_mode(), patch.object(cv_ir_cron, 'request', fake_request):
            self.cron.method_direct_trigger()
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(row.type, 'manual')
        self.assertEqual(row.user_id, operator)

    def test_run_manually_records_a_failure(self):
        with (
            self.enter_registry_test_mode(),
            self.assertLogs('odoo.addons.base.models.ir_cron', 40),
            self.registry.cursor() as cron_cr,
        ):
            result = self.failing_cron.with_env(self.env(cr=cron_cr)).method_direct_trigger()
        # Odoo 19 logs the failure of a manual run and returns True: the
        # history row is what records it.
        self.assertIs(result, True)
        row = self._rows(self.failing_cron)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'fail')
        self.assertIn('lamp broken', row.error)

