/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { patch } from "@web/core/utils/patch";

patch(SearchBar.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasCustomGroup = await this._checkUserGroup();
        });
    },
    async _checkUserGroup() {
        return !await this.__owl__.app.env.services.user.hasGroup("enhanced_security_search.group_custom_search");
    },
    get hideCustomFilter() {
        return this.hasCustomGroup || false;
    },
    onFacetLabelClick(target, facet) {
        if (this.hasCustomGroup) {
            return;
        } else {
            super.onFacetLabelClick(target, facet);
        }
    }
});
