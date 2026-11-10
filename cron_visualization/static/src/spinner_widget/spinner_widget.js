/** @odoo-module **/

import { BooleanField, booleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class SpinnerWidgetField extends BooleanField {
    static template = "spinner_widget";

    get isRunning() {
        return this.props.record.data[this.props.name];
    }

    // Title shown on hover, based on the running state.
    get getSpinnerTitle() {
        return this.isRunning ? _t("Running") : _t("Stopped");
    }
}

export const spinnerWidgetField = {
    ...booleanField,
    component: SpinnerWidgetField,
};

registry.category("fields").add("spinner_widget", spinnerWidgetField);
