import { Component, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Read-only rendering of an import/export manifest (JSON text field) as a
 * table of the exports it contains.
 */
export class IerManifestField extends Component {
    static template = "import_export_records.IerManifestField";

    props = useProps({ ...standardFieldProps });

    get manifest() {
        const value = this.props.record.data[this.props.name];
        if (!value) {
            return false;
        }
        try {
            const manifest = JSON.parse(value);
            return manifest && Array.isArray(manifest.ir_exports) ? manifest : false;
        } catch {
            return false;
        }
    }
}

export const ierManifestField = {
    component: IerManifestField,
    displayName: _t("IER Manifest"),
    supportedTypes: ["text", "char"],
};

registry.category("fields").add("ier_manifest", ierManifestField);
