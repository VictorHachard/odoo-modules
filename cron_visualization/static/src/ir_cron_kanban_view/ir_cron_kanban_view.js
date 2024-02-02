/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { IrCronKanbanRenderer } from "@cron_visualization/ir_cron_kanban_view/ir_cron_kanban_renderer";
import { IrCronKanbanController } from "@cron_visualization/ir_cron_kanban_view/ir_cron_kanban_controller";

export const IrCronKanbanView = {
    ...kanbanView,
    Model: RelationalModel,
    Renderer: IrCronKanbanRenderer,
    Controller: IrCronKanbanController,
//    buttonTemplate: "cron_visualization.KanbanView.Buttons",
};

registry.category("views").add("ir_cron_kanban", IrCronKanbanView);
