/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

// Not imported from search_bar.js: this file lives in the lazy bundle, and
// keeping it free of dependencies on the main one keeps the load order moot.
const CUSTOM_SEARCH_GROUP = "enhanced_security_search.group_custom_search";

// The pivot header carries its own "Add Custom Group" control, independent of
// the one in the search panel: same getter name, different component. Patching
// SearchBarMenu alone left every pivot view offering the full field list.
patch(PivotRenderer.prototype, {
    setup() {
        super.setup();
        this.hideCustomSearch = true;
        onWillStart(async () => {
            this.hideCustomSearch = !(await user.hasGroup(CUSTOM_SEARCH_GROUP));
        });
    },
    get hideCustomGroupBy() {
        // Add a reason to hide; the view's own `hideCustomGroupBy` option still
        // has to be honoured.
        return this.hideCustomSearch || super.hideCustomGroupBy;
    },
});
