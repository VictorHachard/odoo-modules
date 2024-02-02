/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import {_lt} from "@web/core/l10n/translation";

export class IERListBtnController extends ListController {
   setup() {
       super.setup();
   }

   OnImportClick() {
//       this.actionService.doAction({
//          type: 'ir.actions.act_window',
//          res_model: 'ier.import.wizard',
//          name: _lt('Import Records'),
//          view_mode: 'form',
//          view_type: 'form',
//          views: [[false, 'form']],
//          target: 'new',
//          res_id: false,
//      });
   }
}

export const IERTreeView = {
   ...listView,
   Controller: IERListBtnController,
   buttonTemplate: "ier_list_btn",
};

registry.category("views").add("ier_list_btn", IERTreeView);