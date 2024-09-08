/** @odoo-module **/

import VariantMixin from "@website_sale_stock/js/variant_mixin";
import "@website_sale/js/website_sale";
import { renderToElement } from "@web/core/utils/render";

const oldChangeCombinationStock = VariantMixin._onChangeCombinationStock;
/**
 * Displays additional info messages regarding the product's
 * stock and the wishlist.
 *
 * @override
 */
VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    oldChangeCombinationStock.apply(this, arguments);
    if (this.el.querySelector('#stock_notification_div')) {
        const stockNotificationDiv = this.el.querySelector('#stock_notification_div');
        // Remove stockNotificationDiv if out_of_stock_back_in_stock_message is False
        if (!combination.out_of_stock_back_in_stock_message) {
            stockNotificationDiv.remove();
        }
    }
};
