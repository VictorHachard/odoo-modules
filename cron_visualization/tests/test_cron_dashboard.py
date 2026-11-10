from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import CronHistoryCase

COMPUTED = ['cv_history', 'cv_progress_estimated', 'cv_is_running', 'cv_history_count', 'cv_next_execution_timer']


@tagged('post_install', '-at_install')
class TestCronDashboard(CronHistoryCase):
    """The computed fields the kanban dashboard reads on ir.cron."""

    def _refresh(self, *crons):
        for cron in crons or (self.cron,):
            cron.invalidate_recordset(COMPUTED, flush=False)

    def test_history_count(self):
        self._run()
        self._run(state='fail')
        self._run(cron=self.other_cron)
        self._refresh(self.cron, self.other_cron)
        self.assertEqual(self.cron.cv_history_count, 2)
        self.assertEqual(self.other_cron.cv_history_count, 1)

    def test_history_count_without_runs(self):
        self.assertEqual(self.cron.cv_history_count, 0)

    def test_is_running(self):
        self.assertFalse(self.cron.cv_is_running)
        self._run(state='running')
        self._refresh()
        self.assertTrue(self.cron.cv_is_running)
        self.assertFalse(self.other_cron.cv_is_running)

    def test_running_filter(self):
        self._run(state='running')
        self._run(cron=self.other_cron, state='success')
        Cron = self.env['ir.cron'].with_context(active_test=False)
        ours = self.cron | self.other_cron
        self.assertEqual(Cron.search([('cv_is_running', '=', True), ('id', 'in', ours.ids)]), self.cron)
        self.assertEqual(Cron.search([('cv_is_running', '!=', True), ('id', 'in', ours.ids)]), self.other_cron)
        self.assertEqual(Cron.search([('cv_is_running', '=', False), ('id', 'in', ours.ids)]), self.other_cron)

    def test_running_filter_of_the_search_view(self):
        self._run(state='running')
        action_domain = [('cv_is_running', '=', True)]
        found = self.env['ir.cron'].with_context(active_test=False).search(action_domain)
        self.assertIn(self.cron, found)
        self.assertNotIn(self.other_cron, found)

    def test_history_string_is_the_last_ten_runs_oldest_first(self):
        for i in range(12):
            self._run(state='fail' if i == 11 else 'success', duration=float(i))
        self._run(cron=self.other_cron, duration=99.0)
        self._refresh(self.cron, self.other_cron)
        runs = self.cron.cv_history.split(',')
        self.assertEqual(len(runs), 10)
        self.assertEqual(runs[0], 'success;2.0')
        self.assertEqual(runs[-1], 'fail;11.0')
        self.assertEqual(self.other_cron.cv_history, 'success;99.0')

    def test_raw_sql_computes_see_unflushed_writes(self):
        row = self._run(state='running', started_ago=timedelta(minutes=1))
        self._refresh()
        self.assertTrue(self.cron.cv_progress_estimated)
        row.write({'state': 'success', 'duration': 3.5})
        self._refresh()
        self.assertEqual(self.cron.cv_history, 'success;3.5')
        self.assertFalse(self.cron.cv_progress_estimated)

    def test_history_string_has_no_none_for_open_rows(self):
        self.History.create({'ir_cron_id': self.cron.id, 'type': 'automatic'})
        interrupted = self.History.create({'ir_cron_id': self.cron.id, 'type': 'automatic'})
        interrupted.state = 'interruption'
        self._refresh()
        self.assertEqual(self.cron.cv_history, 'running;,interruption;')

    def test_history_string_empty_without_runs(self):
        self.assertEqual(self.cron.cv_history, '')

    def test_history_string_on_an_empty_recordset(self):
        self.env['ir.cron'].browse()._compute_cv_history()

    def test_progress_false_when_idle(self):
        self._run()
        self._refresh()
        self.assertFalse(self.cron.cv_progress_estimated)

    def test_progress_from_the_average_of_successful_runs(self):
        for duration in (10.0, 10.0, 10.0):
            self._run(duration=duration)
        self._run(state='fail', duration=1000.0)
        self._run(state='running', started_ago=timedelta(minutes=5))
        self._refresh()
        progress, elapsed, run_type = self.cron.cv_progress_estimated.split(';')
        self.assertAlmostEqual(float(progress), 50, delta=3)
        self.assertAlmostEqual(float(elapsed), 5, delta=0.3)
        self.assertEqual(run_type, 'automatic')

    def test_progress_is_capped_at_99(self):
        self._run(duration=1.0)
        self._run(state='running', started_ago=timedelta(minutes=30))
        self._refresh()
        self.assertEqual(float(self.cron.cv_progress_estimated.split(';')[0]), 99)

    def test_progress_on_the_first_run_is_unknown(self):
        """No successful run to estimate from: no percentage at all, rather
        than a bar claiming 99% from the first second."""
        self._run(state='running', started_ago=timedelta(minutes=1), type='manual')
        self._refresh()
        progress, elapsed, run_type = self.cron.cv_progress_estimated.split(';')
        self.assertEqual(progress, '')
        self.assertAlmostEqual(float(elapsed), 1, delta=0.3)
        self.assertEqual(run_type, 'manual')

    def test_progress_unknown_when_only_failures(self):
        self._run(state='fail', duration=5.0)
        self._run(state='interruption', duration=0.0)
        self._run(state='running', started_ago=timedelta(minutes=1))
        self._refresh()
        self.assertEqual(self.cron.cv_progress_estimated.split(';')[0], '')

    def test_progress_unknown_when_successful_runs_took_no_time(self):
        self._run(duration=0.0)
        self._run(state='running', started_ago=timedelta(minutes=1))
        self._refresh()
        self.assertEqual(self.cron.cv_progress_estimated.split(';')[0], '')

    def test_progress_at_the_very_start_of_a_run(self):
        self._run(duration=10.0)
        self._run(state='running')
        self._refresh()
        progress, elapsed, _type = self.cron.cv_progress_estimated.split(';')
        self.assertLess(float(progress), 5)
        self.assertGreaterEqual(float(elapsed), 0)

    def test_progress_never_negative_with_a_future_start(self):
        """A start a few seconds ahead of this worker's clock (another host)."""
        self._run(duration=10.0)
        row = self._run(state='running')
        row.started_at = fields.Datetime.now() + timedelta(seconds=30)
        self._refresh()
        progress, elapsed, _type = self.cron.cv_progress_estimated.split(';')
        self.assertEqual(float(progress), 0)
        self.assertEqual(float(elapsed), 0)

    def test_progress_uses_only_the_last_ten_successful_runs(self):
        for _i in range(5):
            self._run(duration=100.0)
        for _i in range(10):
            self._run(duration=10.0)
        self._run(state='running', started_ago=timedelta(minutes=5))
        self._refresh()
        self.assertAlmostEqual(float(self.cron.cv_progress_estimated.split(';')[0]), 50, delta=3)

    def test_progress_lists_every_concurrent_run(self):
        self._run(state='running', started_ago=timedelta(minutes=2))
        self._run(state='running', started_ago=timedelta(minutes=1))
        self._refresh()
        self.assertEqual(len(self.cron.cv_progress_estimated.split(',')), 2)

    def test_next_execution_timer(self):
        self.cron.nextcall = fields.Datetime.now() + timedelta(minutes=90)
        self.assertAlmostEqual(self.cron.cv_next_execution_timer, 90, delta=1)
        self.cron.nextcall = fields.Datetime.now() - timedelta(minutes=10)
        self._refresh()
        self.assertAlmostEqual(self.cron.cv_next_execution_timer, -10, delta=1)

    def test_open_history_action(self):
        action = self.cron.open_history()
        self.assertEqual(action['res_model'], 'cv.ir.cron.history')
        self.assertEqual(action['domain'], [('ir_cron_id', '=', self.cron.id)])
        self.assertTrue(action['help'])
        for view_type in action['view_mode'].split(','):
            self.env['cv.ir.cron.history'].get_views([(False, view_type)])

    def test_kanban_reads_every_cron_at_once(self):
        """The dashboard's kanban read over the whole instance, as it happens on each reload."""
        self._run(state='running')
        crons = self.env['ir.cron'].with_context(active_test=False).search([])
        spec = {name: {} for name in (
            'name', 'nextcall', 'interval_number', 'interval_type', 'cv_is_running',
            'cv_next_execution_timer', 'cv_history', 'cv_progress_estimated', 'cv_history_count')}
        records = crons.web_read(spec)
        self.assertEqual(len(records), len(crons))

    def test_dashboard_views_load(self):
        kanban = self.env.ref('cron_visualization.cv_ir_cron_kanban_view')
        arch = kanban.arch
        for widget in ('spinner_widget', 'cron_float_time_day_widget', 'cron_history_widget', 'cron_progressbar_widget'):
            self.assertIn(widget, arch)
        self.assertIn('js_class="ir_cron_kanban"', arch)
        self.env['ir.cron'].get_views([(kanban.id, 'kanban'), (False, 'form'), (False, 'search')])
        self.assertIn('kanban', self.env.ref('base.ir_cron_act').view_mode)

    def test_running_filter_rejects_unsupported_operators(self):
        with self.assertRaises(Exception):
            self.env['ir.cron'].search([('cv_is_running', '>', 1)])

    def test_running_filter_with_no_running_cron(self):
        self.History.search([('state', '=', 'running')]).write({'state': 'success'})
        Cron = self.env['ir.cron'].with_context(active_test=False)
        self.assertFalse(Cron.search([('cv_is_running', '=', True)]))
        self.assertEqual(
            Cron.search_count([('cv_is_running', '=', False)]),
            Cron.search_count([]),
        )

    def test_computes_on_a_new_record(self):
        """The form of a new cron computes everything on a NewId."""
        new = self.env['ir.cron'].new({'name': 'CV draft'})
        self.assertFalse(new.cv_is_running)
        self.assertFalse(new.cv_progress_estimated)
        self.assertEqual(new.cv_history, '')
        self.assertEqual(new.cv_history_count, 0)

    def test_next_execution_timer_is_timezone_independent(self):
        """A duration between two UTC datetimes: the user's tz changes nothing."""
        self.cron.nextcall = fields.Datetime.now() + timedelta(minutes=30)
        for tz in ('UTC', 'Pacific/Kiritimati', 'America/Adak'):
            cron = self.cron.with_context(tz=tz)
            cron.invalidate_recordset(['cv_next_execution_timer'])
            self.assertAlmostEqual(cron.cv_next_execution_timer, 30, delta=1)

    def test_history_action_matches_open_history(self):
        """Both are documented as kept in sync."""
        action = self.env.ref('cron_visualization.cv_ir_cron_history_action')
        opened = self.cron.open_history()
        self.assertEqual(action.res_model, opened['res_model'])
        self.assertEqual(action.view_mode, opened['view_mode'])

    def test_open_history_requires_a_single_cron(self):
        with self.assertRaises(ValueError):
            (self.cron | self.other_cron).open_history()

    def test_history_views_render(self):
        for view_type in ('list', 'form', 'pivot', 'graph', 'calendar', 'search'):
            views = self.env['cv.ir.cron.history'].get_views([(False, view_type)])
            self.assertIn(view_type, views['views'])

    def test_history_count_ignores_other_crons_rows_in_batch(self):
        for _i in range(3):
            self._run(cron=self.other_cron)
        crons = self.cron | self.other_cron
        crons.invalidate_recordset(['cv_history_count'])
        self.assertEqual(crons.mapped('cv_history_count'), [0, 3])

    def test_uninstall_hook_restores_the_cron_action(self):
        from .. import _uninstall_hook
        action = self.env.ref('base.ir_cron_act')
        self.assertEqual(action.view_mode, 'list,kanban,form,calendar')
        _uninstall_hook(self.env)
        self.assertEqual(action.view_mode, 'list,form,calendar')
        # Idempotent.
        _uninstall_hook(self.env)
        self.assertEqual(action.view_mode, 'list,form,calendar')
