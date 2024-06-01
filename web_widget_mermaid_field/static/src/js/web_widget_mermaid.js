/** @odoo-module **/

import { onWillStart, markup } from "@odoo/owl";
import { TextField } from "@web/views/fields/text/text_field";
import { registry } from "@web/core/registry";

export class MermaidField extends TextField {

    static props = {
        ...TextField.props,
        mermaidConfig: { type: Object, optional: true },
    }

    setup() {
        super.setup();
        this.chartId = _.uniqueId("mermaid_chart_");
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

MermaidField.template = "web_widget_mermaid_field.MermaidField";
MermaidField.supportedTypes = ["text"];
MermaidField.props = {
    ...TextField.props,
    mermaidConfig: { type: Object, optional: true },
};
MermaidField.extractProps = ({ attrs }) => ({
    mermaidConfig: attrs.options || {},
});

registry.category("fields").add("mermaid", MermaidField);