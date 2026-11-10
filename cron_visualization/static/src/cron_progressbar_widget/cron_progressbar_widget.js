/** @odoo-module **/

import { ProgressBarField, progressBarField } from "@web/views/fields/progress_bar/progress_bar_field";
import { registry } from "@web/core/registry";
import { formatMinutes, parseEntries } from "@cron_visualization/utils/format";

export class CronProgressbarWidgetField extends ProgressBarField {
    static template = "cron_progressbar_widget";

    /**
     * One bar per currently running execution, parsed from the
     * "progress;duration;type,..." string. `progress` is empty when the server
     * has no successful run to estimate from: the bar is then drawn full and
     * striped, without a percentage (indeterminate).
     */
    get getProgressBar() {
        return parseEntries(this.props.record.data[this.props.name]).map(
            ([progress, duration, type], index) => {
                const value = parseFloat(progress);
                const known = Number.isFinite(value);
                return {
                    known,
                    progress: known ? value : 100,
                    duration: formatMinutes(duration),
                    type,
                    index,
                };
            }
        );
    }
}

export const cronProgressbarWidgetField = {
    ...progressBarField,
    component: CronProgressbarWidgetField,
    supportedTypes: ["char"],
};

registry.category("fields").add("cron_progressbar_widget", cronProgressbarWidgetField);
