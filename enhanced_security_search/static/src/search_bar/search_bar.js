/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

export const CUSTOM_SEARCH_GROUP = "enhanced_security_search.group_custom_search";

patch(SearchBar.prototype, {
    setup() {
        super.setup();
        // `true` until the answer is known: a control must never flash into
        // view for a user who is not allowed to see it. The answer is in the
        // session (see ir_http.py), so this resolves without an RPC.
        this.hideCustomSearch = true;
        onWillStart(async () => {
            this.hideCustomSearch = !(await user.hasGroup(CUSTOM_SEARCH_GROUP));
        });
    },
    get hideCustomFilter() {
        return this.hideCustomSearch;
    },
    selectItem(item) {
        // The "Custom Filter..." entry of the autocomplete is removed from the
        // template; refuse it here too, so no keyboard path reaches the dialog.
        if (this.hideCustomFilter && item?.isAddCustomFilterButton) {
            return;
        }
        return super.selectItem(...arguments);
    },
    onFacetLabelClick(facet) {
        // Core's handler does two unrelated things: it toggles the group-by
        // sort order, and only otherwise opens the domain editor. Withhold the
        // domain editor alone; the sort toggle has nothing to do with custom
        // filters and returning early for the whole handler silently took it
        // away.
        const sortsGroupBy =
            this.env.searchModel.canOrderByCount && facet.type === "groupBy";
        if (this.hideCustomFilter && facet.domain && !sortsGroupBy) {
            return;
        }
        return super.onFacetLabelClick(facet);
    },
});
