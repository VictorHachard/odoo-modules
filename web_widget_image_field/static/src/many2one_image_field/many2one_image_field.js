import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export class Many2OneImageField extends Component {
    static template = "web_widget_image_field.Many2OneImageField";
    static components = { Many2One };
    props = useProps({
        ...many2OneFieldProps,
        imageField: t.string().optional("image_128"),
    });

    get m2oProps() {
        return computeM2OProps(this.props);
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get imageUrl() {
        const unique = this.value.write_date ? `?unique=${this.value.write_date.toMillis()}` : "";
        return `/web/image/${this.relation}/${this.value.id}/${this.props.imageField}${unique}`;
    }
}

const descriptor = buildM2OFieldDescription(Many2OneImageField);

export const many2OneImageField = {
    ...descriptor,
    displayName: _t("Many2one with image"),
    supportedOptions: [
        ...descriptor.supportedOptions,
        {
            label: _t("Image Field"),
            name: "image_field",
            type: "string",
            help: _t("The field of the related record to display as image (image_128 by default)."),
        },
    ],
    relatedFields: [{ name: "write_date", type: "datetime" }],
    additionalClasses: ["o_field_many2one_image"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canOpen:
                "no_open" in staticInfo.options
                    ? !staticInfo.options.no_open
                    : staticInfo.viewType === "form",
            imageField: staticInfo.options.image_field || "image_128",
        };
    },
};

registry.category("fields").add("many2one_image", many2OneImageField);
