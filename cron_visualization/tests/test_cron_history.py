from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from ..model import cv_ir_cron_history
from ..model.cv_ir_cron_history import (
    CRON_BUS_CHANNEL, DEFAULT_RETENTION_DAYS, RETENTION_PARAM,
)
from .common import CronHistoryCase


@tagged('post_install', '-at_install')
class TestCronHistory(CronHistoryCase):
    """The run history rows: lifecycle, notifications, stale sweep and GC."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_defaults(self):
        row = self.History.create({'ir_cron_id': self.cron.id})
        self.assertEqual(row.state, 'running')
        self.assertEqual(row.user_id, self.env.user)
        self.assertTrue(row.started_at)
        self.assertFalse(row.ended_at)
        self.assertEqual(row.display_name, 'CV test cron')

    def test_display_name_follows_the_cron(self):
        row = self._run()
        self.cron.name = 'CV renamed cron'
        self.assertEqual(row.display_name, 'CV renamed cron')

    def test_model_and_field_names_stay_compatible_with_17(self):
        """Existing 17.0 installs upgrade in place: same model, same columns."""
        fields_ = self.env['cv.ir.cron.history']._fields
        for name in ('ir_cron_id', 'user_id', 'type', 'state', 'started_at', 'ended_at', 'duration', 'error'):
            self.assertIn(name, fields_)
            self.assertTrue(fields_[name].store, name)
        self.assertEqual(
            [key for key, _label in fields_['state'].selection],
            ['success', 'fail', 'interruption', 'running'],
        )
        self.assertEqual([key for key, _label in fields_['type'].selection], ['manual', 'automatic'])
        for xmlid in (
            'cron_visualization.cv_ir_cron_history_view_form',
            'cron_visualization.cv_ir_cron_history_view_tree',
            'cron_visualization.cv_ir_cron_history_view_calendar',
            'cron_visualization.cv_ir_cron_history_view_pivot',
            'cron_visualization.cv_ir_cron_history_view_graph',
            'cron_visualization.cv_ir_cron_history_view_search',
            'cron_visualization.cv_ir_cron_history_action',
            'cron_visualization.ir_cron_view_form_inherit',
            'cron_visualization.ir_cron_view_search_inherit',
            'cron_visualization.cv_ir_cron_kanban_view',
            'cron_visualization.access_cv_ir_cron_history_group_cron',
        ):
            self.assertTrue(self.env.ref(xmlid, raise_if_not_found=False), xmlid)

    def test_create_notifies_the_dashboard_with_cron_ids_only(self):
        with self._capture_bus() as sent:
            self.History.create([
                {'ir_cron_id': self.cron.id},
                {'ir_cron_id': self.other_cron.id},
            ])
        self.assertEqual(len(sent), 1)
        notification_type, payload = sent[0]
        self.assertEqual(notification_type, self.NOTIFICATION)
        self.assertEqual(sorted(payload['cron_ids']), sorted([self.cron.id, self.other_cron.id]))
        self.assertEqual(list(payload), ['cron_ids'])

    def test_notification_really_reaches_the_bus(self):
        bus = self.env['bus.bus'].sudo()
        domain = [('channel', 'ilike', CRON_BUS_CHANNEL)]
        before = bus.search_count(domain)
        self.History.create({'ir_cron_id': self.cron.id})
        self.env.cr.precommit.run()
        self.assertEqual(bus.search_count(domain), before + 1)

    def test_notification_does_not_go_to_the_settings_group(self):
        """One row per run on a dedicated channel, not one per group member page."""
        bus = self.env['bus.bus'].sudo()
        group_channel = '"res.groups", %s' % self.env.ref('base.group_system').id
        before = bus.search_count([('channel', 'like', group_channel)])
        self.History.create({'ir_cron_id': self.cron.id})
        self.env.cr.precommit.run()
        self.assertEqual(bus.search_count([('channel', 'like', group_channel)]), before)

    def test_finish_success(self):
        row = self._run(state='running', started_ago=timedelta(minutes=6))
        with self._capture_bus() as sent:
            row.finish(True)
        self.assertEqual(row.state, 'success')
        self.assertTrue(row.ended_at)
        self.assertAlmostEqual(row.duration, 6, delta=0.2)
        self.assertFalse(row.error)
        self.assertEqual(len(sent), 1)

    def test_finish_failure_keeps_the_error(self):
        row = self._run(state='running')
        row.finish(False, 'ZeroDivisionError: division by zero')
        self.assertEqual(row.state, 'fail')
        self.assertEqual(row.error, 'ZeroDivisionError: division by zero')

    def test_finish_failure_without_message(self):
        row = self._run(state='running')
        row.finish(False)
        self.assertEqual(row.state, 'fail')
        self.assertFalse(row.error)

    def test_finish_requires_a_single_row(self):
        rows = self._run(state='running') | self._run(state='running')
        with self.assertRaises(ValueError):
            rows.finish(True)

    def test_resume_puts_a_closed_row_back_to_running(self):
        row = self._run(state='running')
        row.finish(True)
        with self._capture_bus() as sent:
            row.resume()
        self.assertEqual(row.state, 'running')
        self.assertFalse(row.ended_at)
        self.assertEqual(len(sent), 1)

    def test_resume_on_a_running_row_is_a_no_op(self):
        row = self._run(state='running')
        with self._capture_bus() as sent:
            row.resume()
        self.assertEqual(row.state, 'running')
        self.assertFalse(sent)

    def test_duration_spans_every_iteration_of_a_run(self):
        row = self._run(state='running', started_ago=timedelta(minutes=10))
        row.finish(True)
        row.resume()
        row.finish(True)
        self.assertAlmostEqual(row.duration, 10, delta=0.2)

    def test_history_goes_with_its_cron(self):
        row = self._run(cron=self.other_cron)
        self.other_cron.unlink()
        self.assertFalse(row.exists())

    # ------------------------------------------------------------------
    # Stale sweep: a run is alive while its worker holds the cron lock
    # ------------------------------------------------------------------

    def test_running_row_of_a_dead_worker_is_interrupted(self):
        """Nobody holds the cron row: whoever started the run is gone, however
        recent the run is."""
        dead = self._run(state='running', started_ago=timedelta(minutes=2))
        done = self._run(state='success')
        with self._capture_bus() as sent:
            closed = self.History._close_stale_running()
        self.assertEqual(closed, dead)
        self.assertEqual(dead.state, 'interruption')
        self.assertTrue(dead.ended_at)
        self.assertEqual(done.state, 'success')
        self.assertEqual(len(sent), 1)

    def test_run_of_a_live_worker_is_left_alone(self):
        """However old: a nightly batch may legitimately run for more than a day."""
        busy_cron = self.env.ref('base.autovacuum_job')
        alive = self._run(cron=busy_cron, state='running', started_ago=timedelta(days=3))
        dead = self._run(state='running', started_ago=timedelta(days=3))
        with self._held_by_another_worker(busy_cron):
            closed = self.History._close_stale_running()
        self.assertEqual(closed, dead)
        self.assertEqual(alive.state, 'running')
        self.assertEqual(dead.state, 'interruption')

    def test_stale_sweep_without_running_rows(self):
        self._run(state='success')
        with self._capture_bus() as sent:
            self.assertFalse(self.History._close_stale_running())
        self.assertFalse(sent)

    def test_stale_sweep_runs_as_superuser(self):
        employee = self.env['res.users'].create({
            'name': 'CV sweep employee', 'login': 'cv_sweep_employee',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        dead = self._run(state='running')
        self.History.with_user(employee)._close_stale_running()
        self.assertEqual(dead.state, 'interruption')

    def test_register_hook_runs_the_stale_sweep(self):
        dead = self._run(state='running', started_ago=timedelta(hours=1))
        self.History._register_hook()
        self.assertEqual(dead.state, 'interruption')

    def test_interrupted_run_is_no_longer_running(self):
        self._run(state='running')
        self.History._close_stale_running()
        self.cron.invalidate_recordset(['cv_is_running', 'cv_progress_estimated'])
        self.assertFalse(self.cron.cv_is_running)
        self.assertFalse(self.cron.cv_progress_estimated)

    # ------------------------------------------------------------------
    # Retention / garbage collection
    # ------------------------------------------------------------------

    def test_gc_deletes_old_rows_and_sweeps_stale_runs(self):
        old = self._run()
        recent = self._run()
        stale = self._run(state='running', started_ago=timedelta(hours=2))
        self._backdate_create(old, timedelta(days=DEFAULT_RETENTION_DAYS + 1))
        done, remaining = self.History._gc_history()
        self.assertEqual((done, remaining), (1, 0))
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertEqual(stale.state, 'interruption')

    def test_gc_keeps_rows_inside_the_retention(self):
        row = self._run()
        self._backdate_create(row, timedelta(days=DEFAULT_RETENTION_DAYS - 1))
        self.assertEqual(self.History._gc_history(), (0, 0))
        self.assertTrue(row.exists())

    def test_gc_reports_the_backlog_in_batches(self):
        rows = self._run() | self._run() | self._run()
        self._backdate_create(rows, timedelta(days=100))
        with patch.object(cv_ir_cron_history, 'GC_BATCH_SIZE', 2):
            done, remaining = self.History._gc_history()
            self.assertEqual(done, 2)
            self.assertEqual(remaining, 1)
            done, remaining = self.History._gc_history()
        self.assertEqual((done, remaining), (1, 0))
        self.assertFalse(rows.exists())

    def test_gc_is_registered_as_autovacuum(self):
        self.assertTrue(getattr(type(self.History)._gc_history, '_autovacuum', False))

    def test_retention_from_the_system_parameter(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(RETENTION_PARAM, '7')
        self.assertEqual(self.History._get_retention_days(), 7)
        week_old = self._run()
        fresh = self._run()
        self._backdate_create(week_old, timedelta(days=8))
        self._backdate_create(fresh, timedelta(days=6))
        self.assertEqual(self.History._gc_history(), (1, 0))
        self.assertFalse(week_old.exists())
        self.assertTrue(fresh.exists())

    def test_invalid_retention_falls_back_to_the_default(self):
        params = self.env['ir.config_parameter'].sudo()
        for value in ('0', '-3'):
            params.set_param(RETENTION_PARAM, value)
            self.assertEqual(self.History._get_retention_days(), DEFAULT_RETENTION_DAYS, value)
        params.set_param(RETENTION_PARAM, '')
        self.assertEqual(self.History._get_retention_days(), DEFAULT_RETENTION_DAYS)
        params.set_param(RETENTION_PARAM, 'ninety')
        # The unparsable value is logged; the GC must not crash on it.
        with self.assertLogs(cv_ir_cron_history.__name__, 'WARNING'):
            self.assertEqual(self.History._get_retention_days(), DEFAULT_RETENTION_DAYS)
        params.set_param(RETENTION_PARAM, False)
        self.assertEqual(self.History._get_retention_days(), DEFAULT_RETENTION_DAYS)

    def test_gc_with_an_empty_table(self):
        self.History.search([]).unlink()
        self.assertEqual(self.History._gc_history(), (0, 0))

    def test_started_at_is_a_utc_naive_datetime(self):
        """Stored like every Datetime: UTC, naive. The durations and the
        countdown are differences of two such values, never local times."""
        row = self._run()
        self.assertIsNone(row.started_at.tzinfo)
        self.assertLess(abs((fields.Datetime.now() - row.started_at).total_seconds()), 60)
