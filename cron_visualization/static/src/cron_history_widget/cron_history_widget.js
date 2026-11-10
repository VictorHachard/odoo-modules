/** @odoo-module **/

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { formatMinutes, parseEntries } from "@cron_visualization/utils/format";

export class CronHistoryWidgetField extends CharField {
    static template = "cron_history_widget";

    /**
     * The "state;duration,state;duration,..." string, oldest run first, as a
     * list of dots. A getter rather than a parse in setup(): a value read once
     * goes stale as soon as the record is updated in place.
     */
    get getCronHistory() {
        return parseEntries(this.props.record.data[this.props.name]).map(
            ([state, duration], index) => ({
                state,
                // The server sends minutes; empty for running/interrupted rows.
                duration: formatMinutes(duration),
                index,
            })
        );
    }
}

export const cronHistoryWidgetField = {
    ...charField,
    component: CronHistoryWidgetField,
};

registry.category("fields").add("cron_history_widget", cronHistoryWidgetField);
