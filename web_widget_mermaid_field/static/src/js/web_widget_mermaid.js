/** @odoo-module **/

import { onWillStart, onWillPatch, useState, markup } from "@odoo/owl";
import { TextField } from "@web/views/fields/text/text_field";
import { registry } from "@web/core/registry";

export class MermaidField extends TextField {

    static props = {
        ...TextField.props,
        mermaidConfig: { type: Object, optional: true },
    }

    setup() {
        super.setup();
        const { mermaid_scroll_x, division_ration, ...mermaidConfig } = this.props.mermaidConfig;
        this.config = Object.assign({}, {
            logLevel: "fatal",
            securityLevel: "strict",
            startOnLoad: false,
        }, mermaidConfig);
        this.state = useState({
            style: mermaid_scroll_x ? 'overflow-x: auto;' : '',
            subStyle: this.subStyle,
            mermaidSvg: "",
            chartId: "",
            data: "",
        });

        onWillStart(async () => {
            if (this.props.record.data[this.props.name]) {
                await this.renderMermaid();
            }
        });

        onWillPatch(async () => {
            // TODO: Check if this is the best way to update the mermaid chart
            if (this.props.record.data[this.props.name] && this.props.record.data[this.props.name] !== this.state.data) {
                await this.renderMermaid();
            }
       });

    }

    async renderMermaid() {
        try {
            const chartId = _.uniqueId("mermaid_chart_");
            const { svg } = await mermaid.render(chartId, this.props.record.data[this.props.name]);
            let maxWidth = parseFloat($(svg).css("max-width"));
            if (this.props.mermaidConfig.division_ration) {
                const ratio = parseFloat(this.props.mermaidConfig.division_ration);
                maxWidth = maxWidth / ratio;
            }
            this.state.subStyle = `width: ${maxWidth}px;`;
            this.state.mermaidSvg = markup(svg);
            this.state.chartId = chartId;
            this.state.data = this.props.record.data[this.props.name];
        } catch (e) {
            this.state.mermaidSvg = `<pre>${e.message || e.str}</pre>`;
        }
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