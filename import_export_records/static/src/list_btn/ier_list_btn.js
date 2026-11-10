import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class IERListBtnController extends listView.Controller {
    onImportClick() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ier.import.wizard",
            name: _t("Import Records"),
            views: [[false, "form"]],
            target: "new",
        });
    }
}

export const IERListView = {
    ...listView,
    Controller: IERListBtnController,
    buttonTemplate: "import_export_records.ListView.Buttons",
};

registry.category("views").add("ier_list_btn", IERListView);
