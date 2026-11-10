/** @odoo-module **/

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { reactive, useState, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { formatCountdown } from "@cron_visualization/utils/format";

// One 1 Hz tick shared by every card, refcounted, instead of one setInterval per
// card: the ungrouped kanban shows every cron of the instance, so this used to
// start ~50 timers for a page support tends to leave open. Each widget keeps its
// own baseline so the countdown still resets when its own props are updated.
//
// The value is a *duration* (minutes until `nextcall`, both ends computed
// server-side in UTC), so neither the browser time zone nor the user's tz
// preference plays any part, and a skewed client clock does not either: only
// the elapsed ticks are measured locally.
const sharedTick = reactive({ seconds: 0 });
let tickWatchers = 0;
let tickInterval = null;

function startSharedTick() {
    tickWatchers++;
    if (!tickInterval) {
        tickInterval = setInterval(() => (sharedTick.seconds += 1), 1000);
    }
}

function stopSharedTick() {
    tickWatchers = Math.max(0, tickWatchers - 1);
    if (!tickWatchers && tickInterval) {
        clearInterval(tickInterval);
        tickInterval = null;
    }
}

/** Number of widgets currently holding the shared tick (used by the tests). */
export function getTickWatchers() {
    return tickWatchers;
}

export class CronFloatTimeDayWidget extends CharField {
    static template = "cron_float_time_day_widget";

    setup() {
        super.setup();
        // Live countdown: the field holds minutes-until-next-execution computed
        // server-side; we tick locally every second so the value visibly counts
        // down between data reloads, and reset the offset when fresh data
        // arrives (bus-triggered reload changes the props).
        this.tick = useState(sharedTick);
        this.tickOrigin = sharedTick.seconds;
        startSharedTick();
        onWillUpdateProps(() => (this.tickOrigin = sharedTick.seconds));
        onWillUnmount(stopSharedTick);
    }

    get formattedValue() {
        const base = this.props.record.data[this.props.name]; // minutes
        if (typeof base !== "number") {
            return "";
        }
        const elapsed = this.tick.seconds - this.tickOrigin;
        return formatCountdown(base - elapsed / 60);
    }
}

export const cronFloatTimeDayWidget = {
    ...charField,
    component: CronFloatTimeDayWidget,
    supportedTypes: ["float"],
};

registry.category("fields").add("cron_float_time_day_widget", cronFloatTimeDayWidget);
