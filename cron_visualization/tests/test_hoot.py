from odoo.tests import HttpCase, tagged

from odoo.addons.web.tests.test_js import unit_test_error_checker


@tagged('post_install', '-at_install')
class TestCronVisualizationHoot(HttpCase):
    """The Hoot suite of this module (static/tests), on its own.

    Odoo 18 runs the Hoot unit tests only as one suite of every installed
    module (`web` `WebSuite.test_unit_desktop`); the filter keeps this run to
    the tests of this module.
    """

    def test_hoot_desktop(self):
        self.browser_js(
            '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=%40cron_visualization',
            '', '', login='admin', timeout=900,
            success_signal='[HOOT] test suite succeeded',
            error_checker=unit_test_error_checker,
        )
