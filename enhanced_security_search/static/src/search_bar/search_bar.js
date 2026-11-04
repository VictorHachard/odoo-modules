/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

patch(SearchBar.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasCustomGroup = await this._checkUserGroup();
        });
    },
    async _checkUserGroup() {
        return !await user.hasGroup("enhanced_security_search.group_custom_search");
    },
    get hideCustomFilter() {
        return this.hasCustomGroup || false;
    },
    selectItem(item) {
        // The "Custom Filter..." entry of the autocomplete is hidden in the
        // template; refuse it here too, so no keyboard path opens the dialog.
        if (this.hideCustomFilter && item?.isAddCustomFilterButton) {
            return;
        }
        return super.selectItem(...arguments);
    },
    onFacetLabelClick(target, facet) {
        // Core's handler toggles the group-by sort order, and only otherwise
        // opens the domain editor: withhold the domain editor alone.
        const sortsGroupBy = this.env.searchModel.canOrderByCount && facet.type === "groupBy";
        if (this.hideCustomFilter && !sortsGroupBy) {
            return;
        }
        return super.onFacetLabelClick(target, facet);
    }
});
