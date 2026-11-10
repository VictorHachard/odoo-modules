# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, tagged

# Polls the DOM for each selector in turn, clicking the ones flagged so.
STEPS_JS = """
(async () => {
    const steps = %s;
    const deadline = Date.now() + 30000;
    for (const [selector, click] of steps) {
        let el;
        while (!(el = document.querySelector(selector))) {
            if (Date.now() > deadline) {
                console.error("Element not found: " + selector);
                return;
            }
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
        if (click) {
            el.click();
        }
    }
    console.log("test successful");
})();
"""


@tagged('post_install', '-at_install')
class TestIERUi(HttpCase):

    def _run_steps(self, url, steps):
        self.browser_js(url, STEPS_JS % json.dumps(steps), login='admin', timeout=90)

    def test_list_import_button_opens_wizard(self):
        self._run_steps('/odoo/action-import_export_records.ier_template_action', [
            ['.o_list_view .o_data_row', False],
            ['.o_ier_import_button', True],
            ['.modal .ier_import_wizard', False],
        ])

    def test_history_manifest_widget(self):
        history = self.env['ier.template.action.history'].create({
            'type': 'import',
            'template_name': 'ui.zip',
            'manifest': json.dumps({'ir_exports': [
                {'name': 'UI export', 'model_name': 'res.partner', 'fields': ['id', 'name']},
            ]}),
        })
        self._run_steps(f'/odoo/action-import_export_records.ier_template_action_history_action/{history.id}', [
            ['.ier_manifest_widget .ier_badge', False],
        ])

