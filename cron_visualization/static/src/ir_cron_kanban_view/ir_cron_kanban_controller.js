/** @odoo-module */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { onWillUnmount } from "@odoo/owl";

// Must match CRON_BUS_NOTIFICATION and CRON_BUS_CHANNEL in
// model/cv_ir_cron_history.py. The channel is added on mount and dropped on
// unmount on purpose: on the Settings group channel, which the framework
// subscribes for every member on every page, each cron run was pushed to every
// logged-in administrator whether or not a dashboard was open. `ir.websocket`
// keeps the channel out of reach of anyone outside base.group_system.
const CRON_BUS_NOTIFICATION = "cron_history_update";
const CRON_BUS_CHANNEL = "cron_visualization.dashboard";

export class IrCronKanbanController extends KanbanController {
    setup() {
        super.setup();
        // Live updates: instead of polling on a fixed interval, the backend
        // pushes a notification on the bus whenever a cron run starts or
        // finishes, and we reload the kanban on demand. useDebounced absorbs
        // bursts of notifications and cancels any pending call on unmount.
        this.busService = useService("bus_service");
        this.onCronUpdate = useDebounced(() => this.reloadData(), 400);

        this.busService.subscribe(CRON_BUS_NOTIFICATION, this.onCronUpdate);
        this.busService.addChannel(CRON_BUS_CHANNEL);
        onWillUnmount(() => {
            this.busService.unsubscribe(CRON_BUS_NOTIFICATION, this.onCronUpdate);
            this.busService.deleteChannel(CRON_BUS_CHANNEL);
        });
    }

    async reloadData() {
        if (this.model.root) {
            await this.model.root.load();
            this.render(true);
        }
    }
}
