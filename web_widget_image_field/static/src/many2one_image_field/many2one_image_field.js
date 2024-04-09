/* @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "@web/views/fields/many2one/many2one_field";

// Base
export class Many2OneImageField extends Component {
    get relation() {
        return this.props.relation;
    }
}

Many2OneImageField.template = "web_widget_image_field.Many2OneImageField";
Many2OneImageField.additionalClasses = ["o_field_many2one_avatar", "o_field_many2one_image"];

Many2OneImageField.components = {
    Many2OneField,
};
Many2OneImageField.props = {
    ...Many2OneField.props,
    imageField: { type: String, optional: true },
};
Many2OneImageField.extractProps = ({ attrs }) => {
    return {
        ImageSize: attrs.options.image_field || "image_128",
    };
};

Many2OneImageField.supportedTypes = ["many2one"];

Many2OneImageField.extractProps = Many2OneField.extractProps;

registry.category("fields").add("many2one_image", Many2OneImageField);
