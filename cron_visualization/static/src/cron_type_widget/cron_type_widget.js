/** @odoo-module **/

import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CronTypeWidgetField extends BooleanField {
    static template = 'cron_type_widget'
    setup() {
        super.setup();
    }

    // Method to get the title based on the selected value
    get getTypeTitle() {
        if (this.props.record.data[this.props.name] === 'manual') {
            return _lt("Manual");
        } else if (this.props.record.data[this.props.name] === 'automatic') {
            return _lt("Automatic");
        }
    }
}

export const cronTypeWidgetField = {
    ...BooleanField,
    component: CronTypeWidgetField,
}

registry.category("fields").add("cron_type_widget", cronTypeWidgetField);
