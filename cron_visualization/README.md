# Enhanced Cron Visualization - Odoo 19 Module

Real-time kanban dashboard to monitor the scheduled actions (cron jobs)
running in your Odoo instance.

*by HVG Solutions*

## Features

- **Live kanban dashboard**: updates are pushed in real time through the
  Odoo bus whenever a cron run starts or finishes. No polling, no fixed
  refresh interval. The notifications travel on a dedicated channel that only
  Settings users (`base.group_system`) can subscribe to, and only while the
  dashboard is open.
- **Run history**: every execution is recorded with its state
  (success / failed / interrupted / running), duration, type
  (manual vs automatic), the user who started it and the error message.
  A run of a cron using the progress API (several batches) is one row.
- **Running indicator & estimated progress**: a spinner shows whether a cron
  is currently running, and a progress bar estimates completion from the
  average duration of the last 10 successful runs. Without a successful run to
  compare with, the bar is shown as indeterminate.
- **Next-execution countdown** on each card, ticking every second.
- **History analysis**: list, pivot, graph and calendar views over the run
  history, plus a "History" smart button and a "Running" filter on the
  scheduled actions.

## Notes

- Run history older than 90 days is cleaned up automatically (autovacuum), in
  bounded passes. Set the system parameter
  `cron_visualization.history_retention_days` to change the retention.
- A run whose worker died (server restart, `limit_time_real`, out of memory...)
  is flagged as *interrupted*: a run is alive exactly as long as its worker
  holds the lock on the cron, so the check never mistakes a long batch for a
  dead one. The sweep runs on registry load and on each autovacuum pass.
- Access is restricted to Settings / Technical users (`base.group_system`).
- Upgrading from the 17.0 `cron_visualization` keeps the existing history:
  same model (`cv.ir.cron.history`), same fields, same XML ids.
