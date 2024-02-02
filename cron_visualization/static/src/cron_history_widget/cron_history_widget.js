/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { formatFloatTime } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CronHistoryWidgetField extends CharField {
    static template = 'cron_history_widget'

    setup() {
        super.setup();
        this.cron_history = []; // List of dictionaries with state failure and duration
        let value = this.props.record.data[this.props.name];
        if (value && value.includes(',')) {
            let items = value.split(',');
            for (let index = 0; index < items.length; index++) {
                let item = items[index];
                let [state, duration] = item.split(';');
                this.cron_history.push({ state: state, duration: formatFloatTime(duration), index: index });
            }
        } else if (value && value.includes(';')) {
            let [state, duration] = value.split(';');
            this.cron_history.push({state: state, duration: formatFloatTime(duration), index: 1});
        }
    }

    get getCronHistory() {
        return this.cron_history;
    }
}

export const cronHistoryWidgetField = {
    ...CharField,
    component: CronHistoryWidgetField,
}

registry.category("fields").add("cron_history_widget", cronHistoryWidgetField);
