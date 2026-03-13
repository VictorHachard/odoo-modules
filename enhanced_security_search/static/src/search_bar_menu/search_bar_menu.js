/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

patch(SearchBarMenu.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasCustomGroup = await this._checkUserGroup();
        });
    },
    async _checkUserGroup() {
        return !await user.hasGroup("enhanced_security_search.group_custom_search");
    },
    get hideCustomGroupBy() {
        return this.hasCustomGroup || false;
    },
    get hideCustomFilter() {
        return this.hasCustomGroup || false;
    },
});

