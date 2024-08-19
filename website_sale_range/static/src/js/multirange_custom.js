odoo.define('website_sale_range.multirange_inherit', function (require) {
    'use strict';

var multirange = require('website_sale.multirange');
var Multirange = multirange.Multirange;

// Extend the Multirange class using ES6 class syntax
class MultirangeExtended extends Multirange {
    formatNumber(number) {
        let format = this.input.getAttribute("format") || false;  // 'integer', false
        let uom = this.input.getAttribute("uom") || false;
        if (format === 'integer') {
            let parsed = parseInt(number, 10);
            parsed = parsed.toLocaleString();
            return uom ? parsed + ' ' + uom : parsed;
        } else if (format === 'integer_no_locale') {
            let parsed = parseInt(number, 10);
            return uom ? parsed + uom : parsed;
        } else if (format === 'float') {
            let parsed = parseFloat(number);
            parsed = parsed.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            return uom ? parsed + ' ' + uom : parsed;
        } else if (format === 'float_no_locale') {
            let parsed = parseFloat(number);
            return uom ? parsed + uom : parsed;
        } else {
            return super.formatNumber(number);
        }
    }
}

// Override the init function in the original module
multirange.init = function(input, options) {
    return new MultirangeExtended(input, options);
};

// Return the modified module
return {
    Multirange: MultirangeExtended,
    init: multirange.init
};

});