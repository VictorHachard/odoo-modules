import { Component, useState, onWillStart, onPatched, onMounted, markup } from "@odoo/owl";
import { TextField } from "@web/views/fields/text/text_field";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { uniqueId } from "@web/core/utils/functions";

export class MermaidField extends Component {
    static template = 'web_widget_mermaid_field.MermaidField';

    static props = {
        ...TextField.props,
        mermaidConfig: { type: Object, optional: true },
    };

    setup() {
        onMounted(async () => {
            if (this.props.record.data[this.props.name]) {
                await this.renderMermaid();
            }
        });
        onPatched(async () => {
            if (this.props.record.data[this.props.name] && this.props.record.data[this.props.name] !== this.state.data) {
                await this.renderMermaid();
            }
        });

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
            await loadBundle("web_widget_mermaid_field.mermaid_lib");
        });
    }

    async renderMermaid() {
        try {
            const chartId = uniqueId("mermaid_chart_");
            const { svg } = await mermaid.render(chartId, this.props.record.data[this.props.name]);
            const svgElement = new DOMParser().parseFromString(svg, "image/svg+xml").documentElement;
            const maxWidthRegex = /max-width:\s*([\d.]+)px;/;
            const match = svg.match(maxWidthRegex);
            let maxWidth = match ? parseFloat(match[1]) : 0;
            if (this.props.mermaidConfig.division_ration) {
                const ratio = parseFloat(this.props.mermaidConfig.division_ration);
                maxWidth = maxWidth / ratio;
            }
            this.state.subStyle = `width: ${maxWidth}px;`;
            this.state.mermaidSvg = markup(svg);
            this.state.chartId = chartId;
            this.state.data = this.props.record.data[this.props.name];
        } catch (e) {
            this.state.mermaidSvg = markup(`<pre>${e.message || e.str}</pre>`);
        }
    }
}

export const mermaidField = {
    component: MermaidField,
    supportedTypes: ["text"],
    extractProps: ({ options }) => ({
        mermaidConfig: options || {},
    }),
};

registry.category("fields").add("mermaid", mermaidField);