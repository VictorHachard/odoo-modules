/** @odoo-module **/

import { onWillStart, markup } from "@odoo/owl";
import { TextField } from "@web/views/fields/text/text_field";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

export class MermaidField extends TextField {
    static template = 'web_widget_mermaid_field.MermaidField';

    static props = {
        ...TextField.props,
        mermaidConfig: { type: Object, optional: true },
    }

    setup() {
        super.setup();
        this.chartId = uniqueId("mermaid_chart_");
        const { mermaid_scroll_x, division_ration, ...mermaidConfig } = this.props.mermaidConfig;
        this.config = Object.assign({}, {
            logLevel: "fatal",
            securityLevel: "strict",
            startOnLoad: false,
        }, mermaidConfig);
        this.style = '';
        this.subStyle = '';
        if (mermaid_scroll_x) {
            this.style += 'overflow-x: auto;';
        }
        this.mermaidSvg = "";
        onWillStart(async () => {
            if (this.props.record.data[this.props.name]) {
                try {
                    const { svg } = await mermaid.render(this.chartId, this.props.record.data[this.props.name]);
                    let maxWidth = parseFloat($(svg).css("max-width"));
                    if (division_ration) {
                        const ratio = parseFloat(division_ration);
                        maxWidth = maxWidth / ratio;
                    }
                    this.subStyle = `width: ${maxWidth}px;`;
                    this.mermaidSvg = markup(svg);
                } catch (e) {
                    this.mermaidSvg = `<pre>${e.message || e.str}</pre>`;
                }
            }
        });
    }

}

export const mermaidField = {
    ...TextField,
    component: MermaidField,
    supportedTypes: ["text"],
    extractProps: ({ options }) => ({
        mermaidConfig: options || {},
    }),
}

registry.category("fields").add("mermaid", mermaidField);