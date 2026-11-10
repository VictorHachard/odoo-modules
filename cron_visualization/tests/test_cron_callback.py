from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

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
        for attr in ('key', 'history_id', 'run_id'):
            if hasattr(cv_ir_cron._cron_run, attr):
                delattr(cv_ir_cron._cron_run, attr)
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.commits = []
        stack.enter_context(patch.object(self.env.cr, 'commit', lambda: self.commits.append('commit')))
        stack.enter_context(patch.object(self.env.cr, 'rollback', lambda: self.commits.append('rollback')))

    def _call(self, cron, run_id=None, **context):
        """Call `_callback`; with `run_id`, as one batch of the run `run_id`
        of `_run_job` (which stamps the thread with it)."""
        cron = cron.with_context(**context) if context else cron
        previous = getattr(cv_ir_cron._cron_run, 'run_id', None)
        cv_ir_cron._cron_run.run_id = run_id
        try:
            cron._callback(cron.name, cron.ir_actions_server_id.id)
        finally:
            cv_ir_cron._cron_run.run_id = previous

    @mute_logger('odoo.addons.base.models.ir_cron')
    def _raising(self, exception, cron, run_id=None, **context):
        try:
            self._call(cron, run_id, **context)
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

    @mute_logger('odoo.addons.base.models.ir_cron')
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

        context = {'cron_id': self.cron.id}
        with patch.object(Server, 'run', spy):
            self._call(self.cron, 12345, **context)
            self._call(self.cron, 12345, **context)
            self._call(self.cron, 12345, **context)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(states_during_run, ['running'] * 3)

    def test_a_new_run_gets_a_new_row(self):
        self._call(self.cron, 1, cron_id=self.cron.id)
        self._call(self.cron, 2, cron_id=self.cron.id)
        self.assertEqual(len(self._rows()), 2)

    def test_runs_outside_run_job_never_share_a_row(self):
        self._call(self.cron)
        self._call(self.cron)
        self.assertEqual(len(self._rows()), 2)

    def test_deleted_row_between_iterations_is_recreated(self):
        context = {'cron_id': self.cron.id}
        self._call(self.cron, 99, **context)
        self._rows().unlink()
        self._call(self.cron, 99, **context)
        self.assertEqual(len(self._rows()), 1)
        self.assertEqual(self._rows().state, 'success')

    def test_callback_notifies_the_dashboard(self):
        with self._capture_bus() as sent:
            self._call(self.cron)
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(payload['cron_ids'] == [self.cron.id] for _t, payload in sent))

    def test_success_commit_sequence(self):
        """running row committed, then the action with the closing (the 18
        core `_callback` does not commit)."""
        self._call(self.cron)
        self.assertEqual(self.commits, ['commit', 'commit'])

    @mute_logger('odoo.addons.base.models.ir_cron')
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

        context = {'cron_id': self.cron.id}
        with patch.object(Server, 'run', flaky):
            self._raising(UserError, self.cron, 4242, **context)
            self.assertEqual(self._rows().state, 'fail')
            self._call(self.cron, 4242, **context)
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertTrue(row.ended_at)

    def test_thread_slot_is_per_database(self):
        """A cron thread serves every database; the same cron id and run id
        in another database must not reuse this database's row."""
        first = self._run(state='success')
        cv_ir_cron._cron_run.key = ('some_other_db', self.cron.id, 5)
        cv_ir_cron._cron_run.history_id = first.id
        self._call(self.cron, 5, cron_id=self.cron.id)
        self.assertEqual(len(self._rows()), 2)
        self.assertEqual(first.state, 'success')

    def test_thread_slot_pointing_to_another_cron_is_not_reused(self):
        foreign = self._run(cron=self.other_cron, state='success')
        cv_ir_cron._cron_run.key = (self.env.cr.dbname, self.cron.id, 6)
        cv_ir_cron._cron_run.history_id = foreign.id
        self._call(self.cron, 6, cron_id=self.cron.id)
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

    @contextmanager
    def _registry_test_mode(self):
        """One cursor for every transaction: what the out-of-band history
        transactions of "Run Manually" and the job cursor of `_run_job` use."""
        self.registry.enter_test_mode(self.env.cr)
        try:
            yield
        finally:
            self.registry.leave_test_mode()

    def test_run_manually_records_the_run(self):
        """The real "Run Manually" path, `method_direct_trigger`."""
        operator = new_test_user(self.env, login='cv_operator2', password='Cv-Operator-2026!',
                                 groups='base.group_user,base.group_system')
        seen = []
        Server = type(self.env['ir.actions.server'])
        original = Server.run

        def spy(action):
            self.env.invalidate_all()
            seen.append(self._rows().state)
            return original(action)

        with self._registry_test_mode(), patch.object(Server, 'run', spy):
            self.cron.with_user(operator).method_direct_trigger()
        self.assertEqual(seen, ['running'])
        # The row was closed in another transaction.
        self.env.invalidate_all()
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(row.type, 'manual')
        self.assertEqual(row.user_id, operator)
        self.assertTrue(row.ended_at)
        # Out of band: the request transaction was neither committed nor rolled back.
        self.assertEqual(self.commits, [])

    def test_run_manually_records_a_failure(self):
        with self._registry_test_mode():
            # Not assertRaises: its savepoint would roll the history row back.
            try:
                self.failing_cron.method_direct_trigger()
            except UserError:
                pass
            else:
                self.fail('the cron error was swallowed')
        row = self._rows(self.failing_cron)
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'fail')
        self.assertEqual(row.type, 'manual')
        self.assertIn('lamp broken', row.error)

    def test_run_manually_refused_records_nothing(self):
        employee = new_test_user(self.env, login='cv_trigger_employee', password='Cv-Employee-2026!',
                                 groups='base.group_user')
        with self._registry_test_mode():
            try:
                self.cron.with_user(employee).method_direct_trigger()
            except AccessError:
                pass
            else:
                self.fail('an employee could trigger a cron')
        self.assertFalse(self._rows())

    def test_run_job_shares_one_row_between_batches(self):
        """The real scheduler path: `_run_job` calling `_callback` once per
        batch while the server action reports remaining work."""
        Server = type(self.env['ir.actions.server'])
        batches = []

        def batch(action):
            self.env.invalidate_all()
            batches.append(self._rows().state)
            # The progress API, as a batch server action reports it.
            action.env['ir.cron']._notify_progress(done=1, remaining=2 - len(batches))

        job = {
            'id': self.cron.id,
            'cron_name': self.cron.name,
            'user_id': self.env.uid,
            'lastcall': False,
            'timed_out_counter': 0,
            'active': False,
            'ir_actions_server_id': self.cron.ir_actions_server_id.id,
        }
        with self._registry_test_mode(), patch.object(Server, 'run', batch):
            type(self.env['ir.cron'])._run_job(job)
        self.assertEqual(batches, ['running', 'running'])
        self.env.invalidate_all()
        row = self._rows()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.state, 'success')
        self.assertEqual(row.type, 'automatic')
        self.assertIsNone(getattr(cv_ir_cron._cron_run, 'run_id', None))
