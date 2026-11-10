import { Component, markup, onWillStart, proxy, t, useOnChange, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { uniqueId } from "@web/core/utils/functions";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/** Options of the widget itself, the other options are given to Mermaid. */
const WIDGET_OPTIONS = ["mermaid_scroll_x", "division_ration"];

const DEFAULT_CONFIG = {
    logLevel: "fatal",
    securityLevel: "strict",
    startOnLoad: false,
};

export class MermaidField extends Component {
    static template = "web_widget_mermaid_field.MermaidField";

    props = useProps({
        ...standardFieldProps,
        mermaidConfig: t.object().optional(),
    });

    setup() {
        const options = this.props.mermaidConfig || {};
        this.scrollX = Boolean(options.mermaid_scroll_x);
        this.ratio = parseFloat(options.division_ration) || 0;
        this.config = { ...DEFAULT_CONFIG };
        for (const [key, value] of Object.entries(options)) {
            if (!WIDGET_OPTIONS.includes(key)) {
                this.config[key] = value;
            }
        }
        this.state = proxy({
            svg: "",
            width: 0,
            error: "",
        });
        // Each render gets a number: a slow render finishing after a newer one
        // must not overwrite its result.
        this.renderCount = 0;

        onWillStart(async () => {
            await loadBundle("web_widget_mermaid_field.mermaid_lib");
            await this.renderMermaid(this.value);
        });
        useOnChange(
            () => [this.value],
            (value) => {
                this.renderMermaid(value);
            },
            { initialRun: false }
        );
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get containerStyle() {
        return this.scrollX ? "overflow-x: auto;" : "";
    }

    get chartStyle() {
        return this.state.width ? `width: ${this.state.width}px;` : "";
    }

    async renderMermaid(source) {
        const count = ++this.renderCount;
        if (!source) {
            Object.assign(this.state, { svg: "", width: 0, error: "" });
            return;
        }
        const mermaid = window.mermaid;
        try {
            mermaid.initialize(this.config);
            const { svg } = await mermaid.render(uniqueId("mermaid_chart_"), source);
            if (count !== this.renderCount) {
                return;
            }
            const match = svg.match(/max-width:\s*([\d.]+)px;/);
            let width = match ? parseFloat(match[1]) : 0;
            if (this.ratio) {
                width = width / this.ratio;
            }
            // Mermaid sanitizes the SVG it renders unless the view asks for
            // securityLevel "loose".
            Object.assign(this.state, { svg: markup(svg), width, error: "" });
        } catch (error) {
            if (count !== this.renderCount) {
                return;
            }
            Object.assign(this.state, {
                svg: "",
                width: 0,
                error: error?.message || error?.str || _t("The diagram could not be drawn."),
            });
        }
    }
}

export const mermaidField = {
    component: MermaidField,
    displayName: _t("Mermaid diagram"),
    supportedTypes: ["text"],
    extractProps: ({ options }) => ({
        mermaidConfig: options || {},
    }),
};

registry.category("fields").add("mermaid", mermaidField);
