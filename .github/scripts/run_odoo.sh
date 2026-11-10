#!/usr/bin/env bash
# Usage: run_odoo.sh <modules to install> <test tags>
# Installs the modules on a fresh database with the tests enabled, and fails on
# any ERROR or CRITICAL line: Odoo exits 0 when a test fails, the failure is
# only a log line.
set -euo pipefail

install="$1"
tags="$2"
db="test_$(echo "$install" | md5sum | cut -c1-8)"

python odoo/odoo-bin \
  --addons-path=odoo/addons,odoo/odoo/addons,modules \
  --database="$db" \
  --db_host=localhost --db_port=5432 --db_user=odoo --db_password=odoo \
  --init="$install" \
  --test-enable \
  --test-tags="$tags" \
  --log-level=test \
  --stop-after-init --workers=0 --max-cron-threads=0 \
  2>&1 | tee odoo.log

if grep -E "(ERROR|CRITICAL) $db " odoo.log; then
  echo "::error::errors in the Odoo log"
  exit 1
fi
if ! grep -qE "odoo\.tests\.result: [0-9]+ failed, [0-9]+ error\(s\) of [0-9]+ tests" odoo.log; then
  echo "::warning::no test summary found in the log"
fi
