# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

from odoo.addons.web.tests.test_js import unit_test_error_checker


@tagged('post_install', '-at_install')
class TestEnhancedSecuritySearch(HttpCase):

    def test_enhanced_security_search_js(self):
        """Run the hoot tests of the module (facet click, autocomplete)."""
        self.browser_js(
            '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=%2Fenhanced_security_search%2F',
            "", "", login='admin', timeout=300,
            success_signal="[HOOT] Test suite succeeded", error_checker=unit_test_error_checker,
        )
