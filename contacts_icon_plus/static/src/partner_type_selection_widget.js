import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const CONTACT_ICON = "fa-address-book";

export const SIMPLE_ICONS = {
    individual: "fa-male",
    company: "fa-building",
    employee: "fa-id-badge",
    contact: CONTACT_ICON,
    invoice: CONTACT_ICON,
    delivery: CONTACT_ICON,
    other: CONTACT_ICON,
};

export const DETAILED_ICONS = {
    ...SIMPLE_ICONS,
    invoice: "fa-money",
    delivery: "fa-truck",
    other: "fa-ellipsis-v",
};

/**
 * Read-only icon for the partner contact type selection fields.
 */
export class PartnerIconTypeField extends Component {
    static template = "contacts_icon_plus.PartnerIconTypeField";
    static icons = SIMPLE_ICONS;

    props = useProps({ ...standardFieldProps });

    get value() {
        return this.props.record.data[this.props.name];
    }

    get iconClass() {
        return this.constructor.icons[this.value] || "";
    }

    get title() {
        const selection = this.props.record.fields[this.props.name].selection || [];
        const option = selection.find(([value]) => value === this.value);
        return option ? option[1] : "";
    }
}

export class PartnerIconTypeDetailedField extends PartnerIconTypeField {
    static icons = DETAILED_ICONS;
}

export const partnerIconTypeField = {
    component: PartnerIconTypeField,
    displayName: _t("Partner Type Icon"),
    supportedTypes: ["selection"],
};

export const partnerIconTypeDetailedField = {
    component: PartnerIconTypeDetailedField,
    displayName: _t("Partner Type Icon (Detailed)"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("partner_icon_type", partnerIconTypeField);
registry.category("fields").add("partner_icon_type_all", partnerIconTypeDetailedField);
