/** @odoo-module **/

import { ProgressBarField } from "@web/views/fields/progress_bar/progress_bar_field";
import { formatFloatTime } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CronProgressbarWidgetField extends ProgressBarField {
    static template = 'cron_progressbar_widget'

    setup() {
        super.setup();
        this.progress_bar_data = [];
        let value = this.props.record.data[this.props.name];
        if (value && value.includes(',')) {
            let items = value.split(',');
            for (let index = 0; index < items.length; index++) {
                let item = items[index];
                let [progress, duration, type] = item.split(';');
                this.progress_bar_data.push({ progress: progress, duration: formatFloatTime(duration), type: type, index: index });
            }
        } else if (value) {
            let [progress, duration, type] = value.split(';');
            this.progress_bar_data.push({ progress: progress, duration: formatFloatTime(duration), type: type, index: 0 });
        }
    }

    get getProgressBar() {
        return this.progress_bar_data;
    }
}

export const cronProgressbarWidgetField = {
    ...ProgressBarField,
    component: CronProgressbarWidgetField,
}

registry.category("fields").add("cron_progressbar_widget", cronProgressbarWidgetField);
