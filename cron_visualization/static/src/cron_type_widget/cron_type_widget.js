/** @odoo-module **/

import { BooleanField, booleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class CronTypeWidgetField extends BooleanField {
    static template = "cron_type_widget";

    get value() {
        return this.props.record.data[this.props.name];
    }

    // Title shown on hover, based on the run type.
    get getTypeTitle() {
        if (this.value === "manual") {
            return _t("Manual");
        } else if (this.value === "automatic") {
            return _t("Automatic");
        }
        return "";
    }
}

export const cronTypeWidgetField = {
    ...booleanField,
    component: CronTypeWidgetField,
    supportedTypes: ["selection"],
};

registry.category("fields").add("cron_type_widget", cronTypeWidgetField);
