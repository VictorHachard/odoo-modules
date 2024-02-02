/** @odoo-module */

import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {_lt} from "@web/core/l10n/translation";
import {FloatField} from "@web/views/fields/float/float_field";

const { Component, onPatched, onWillUpdateProps, useRef, useState } = owl;

export class IerManifestWidget extends Component {
    setup() {
        this.manifest = false;
        super.setup();
        onWillUpdateProps((nextProps) => {
            this.formatData(nextProps);
        });
    }

    formatData(props) {
         try {
            this.manifest = JSON.parse(props.value);
         } catch (error) {
            this.manifest = false;
         }
    }
}

IerManifestWidget.displayName = _lt("IER Manifest Widget");
IerManifestWidget.template = "ier_manifest";
IerManifestWidget.props = {
    ...standardFieldProps,
};

registry.category("fields").add("ier_manifest", IerManifestWidget);
