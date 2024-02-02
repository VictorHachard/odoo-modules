/* @odoo-module */

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { many2OneField, Many2OneField } from "@web/views/fields/many2one/many2one_field";

// Base
export class Many2OneImageField extends Component {
    static template = "web_widget_image_field.Many2OneImageField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
    };

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
    }
    get many2OneProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(
                ([key, _val]) => key in this.constructor.components.Many2OneField.props
            )
        );
    }
    get imageSize() {
        return this.props.options.size || 'image_128';
    }
}

export const many2OneImageField = {
    ...many2OneField,
    component: Many2OneImageField,
    additionalClasses: ["o_field_many2one_image"],
    extractProps(fieldInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.canOpen = fieldInfo.viewType === "form";
        props.options = fieldInfo.options;
        return props;
    },
};

registry.category("fields").add("many2one_image", many2OneImageField);
