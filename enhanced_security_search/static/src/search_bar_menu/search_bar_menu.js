/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { CustomFavoriteItem } from "@web/search/custom_favorite_item/custom_favorite_item";
import { patch } from "@web/core/utils/patch";

patch(SearchBarMenu.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasCustomGroup = await this._checkUserGroup();
        });
    },
    async _checkUserGroup() {
        return !await this.__owl__.app.env.services.user.hasGroup("enhanced_security_search.group_custom_search");
    },
    get hideCustomGroupBy() {
        return this.hasCustomGroup || false;
    },
    get hideCustomFilter() {
        return this.hasCustomGroup || false;
    },
});

patch(CustomFavoriteItem.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasCustomGroup = await this._checkUserGroup();
        });
    },
    async _checkUserGroup() {
        return !await this.__owl__.app.env.services.user.hasGroup("enhanced_security_search.group_custom_favorite_share");
    },
    get hideShare() {
        return this.hasCustomGroup || false;
    }
});
