/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { formatFloatTime } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CronFloatTimeDayWidget extends CharField {
    static template = 'cron_float_time_day_widget'

    setup() {
        super.setup();
    }

    get formattedValue() {
        let value = this.props.record.data[this.props.name];
        const days = Math.floor(Math.abs(value) / 1440) // Get the days (60 * 24 = 1440)
        const hours = value / 60 % 24; // Get the remaining hours

        const dayText = days !== 1 ? _lt('days') : _lt('day');

        const dayPart = days > 0 ? `${days} ${dayText} ${_lt('and')} ` : '';

        const timePart = formatFloatTime(hours, { displaySeconds: true }).replace('-', '');

        return value < 0 ? `-${dayPart}${timePart}` : `${dayPart}${timePart}`;
    }

}

export const cronFloatTimeDayWidget = {
    ...CharField,
    component: CronFloatTimeDayWidget,
}

registry.category("fields").add("cron_float_time_day_widget", cronFloatTimeDayWidget);
