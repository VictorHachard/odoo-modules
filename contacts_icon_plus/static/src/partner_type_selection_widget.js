/** @odoo-module **/

import { SelectionField } from "@web/views/fields/selection/selection_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class PartnerIconTypeSelectionWidgetField extends SelectionField {
    static template = 'partner_icon_type_selection_widget'

    // Method to get the title based on the selected value
    get getPartnerIconTypeSelectionTitle() {
        switch (this.props.value) {
            case 'individual':
                return _lt("Individual");
            case 'company':
                return _lt("Company");
            case 'employee':
                return _lt("Employee");
            case 'invoice':
                return _lt("Invoice Address");
            case 'delivery':
                return _lt("Delivery Address");
            case 'private':
                return _lt("Private Address");
            case 'other':
                return _lt("Other Address");
            case 'contact':
                return _lt("Contact");
            default:
                return "";
        }
    }
}

export class PartnerIconTypeSelectionAllWidgetField extends PartnerIconTypeSelectionWidgetField {
    static template = 'partner_icon_type_selection_all_widget'
}

registry.category("fields").add("partner_icon_type", PartnerIconTypeSelectionWidgetField);
registry.category("fields").add("partner_icon_type_all", PartnerIconTypeSelectionAllWidgetField);