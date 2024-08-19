odoo.define('website_sale_range.multi_range_attribute_selector', function (require) {
'use strict';

var publicWidget = require('web.public.widget');


publicWidget.registry.multirangeAttrbiuteSelector = publicWidget.Widget.extend({
    selector: '.o_wsale_products_page',
    events: {
        'newRangeValue .o_wsale_attribute_products_page input[type="range"]': '_onAttributeRangeSelected',
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onAttributeRangeSelected(ev) {
        const range = ev.currentTarget;
        const attribute_id = range.dataset.attribute_id;
        const attribute_values = range.dataset.attribute_values;
        // Values: name-id,name-id
        let attribute_values_dict = {};
        attribute_values.split(',').forEach(function (item) {
            let item_split = item.split('-');
            attribute_values_dict[item_split[0]] = item_split[1];
        });
        // Check input
        for (const [key, value] of Object.entries(attribute_values_dict)) {
            let inputs = document.querySelectorAll('input[value="' + attribute_id + '-' + value + '"]');
            for (let input of inputs) {
                input.checked = parseFloat(range.valueLow) <= key && key <= parseFloat(range.valueHigh);
            }
        }
    },
});
});
