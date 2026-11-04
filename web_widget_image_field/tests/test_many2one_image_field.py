# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

from odoo.addons.web.tests.test_js import unit_test_error_checker


@tagged('post_install', '-at_install')
class TestMany2OneImageField(HttpCase):

    def test_many2one_image_field_js(self):
        """Run the hoot tests of the widget (no_open option)."""
        self.browser_js(
            '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=%2Fweb_widget_image_field%2F',
            "", "", login='admin', timeout=300,
            success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker,
        )
