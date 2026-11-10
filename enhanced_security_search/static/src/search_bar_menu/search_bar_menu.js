/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { CustomFavoriteItem } from "@web/search/custom_favorite_item/custom_favorite_item";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { CUSTOM_SEARCH_GROUP } from "@enhanced_security_search/search_bar/search_bar";

patch(SearchBarMenu.prototype, {
    setup() {
        super.setup();
        // Hidden until the group is known (see search_bar.js).
        this.hideCustomSearch = true;
        onWillStart(async () => {
            this.hideCustomSearch = !(await user.hasGroup(CUSTOM_SEARCH_GROUP));
        });
    },
    get hideCustomGroupBy() {
        // `hideCustomGroupBy` is also a supported view/action option, threaded
        // through the search model. Add a reason to hide, never replace the one
        // the view already gave.
        return this.hideCustomSearch || super.hideCustomGroupBy;
    },
    get hideCustomFilter() {
        return this.hideCustomSearch;
    },
    get otherItems() {
        // "Save current search" posts to ir.filters/create_filter, which the
        // server refuses outside the group. Drop it here so the UI never offers
        // a button that answers with an access error.
        const items = super.otherItems;
        if (!this.hideCustomSearch) {
            return items;
        }
        return items.filter((item) => item.Component !== CustomFavoriteItem);
    },
    onAddCustomFilterClick() {
        if (this.hideCustomFilter) {
            return;
        }
        return super.onAddCustomFilterClick(...arguments);
    },
    onAddCustomDateFilterClick() {
        // "Custom Date..." (new in Odoo 20) opens the very same domain editor
        // as "Custom Filter...", only prefilled with a date condition: any
        // field of the model can then be filtered on from there.
        if (this.hideCustomFilter) {
            return;
        }
        return super.onAddCustomDateFilterClick(...arguments);
    },
    onAddCustomGroup() {
        if (this.hideCustomGroupBy) {
            return;
        }
        return super.onAddCustomGroup(...arguments);
    },
});
