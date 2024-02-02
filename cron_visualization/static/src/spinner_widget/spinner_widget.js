/** @odoo-module **/

import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class SpinnerWidgetField extends BooleanField {
    static template = 'spinner_widget'

    // Method to get the title based on the selected value
    get getSpinnerTitle() {
        return this.props.value ? _lt("Running") : _lt("Stopped");
    }
}

export const spinnerWidgetField = {
    ...BooleanField,
    component: SpinnerWidgetField,
}

registry.category("fields").add("spinner_widget", spinnerWidgetField);
