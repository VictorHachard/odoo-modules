odoo.define("web_widget_mermaid_field.web_widget_mermaid_field", function (require) {
    "use strict";

    var basic_fields = require("web.basic_fields");
    var field_registry = require("web.field_registry");

    var defaultConfig = {
        logLevel: "fatal",
        securityLevel: "strict",
        startOnLoad: false, // Rendering is initiated manually
    };

    var MermaidField = basic_fields.FieldText.extend({
        init: function () {
            this._super.apply(this, arguments);
            this.chartId = _.uniqueId("mermaid_chart_");
        },
        className: "o_form_field_mermaid",
        _renderReadonly: function () {
            if (!this.value) {
                return;
            }
            const { mermaid_scroll_x, division_ration, ...mermaidConfig } = this.attrs.options;
            var config = _.extend({}, defaultConfig, mermaidConfig);
            mermaid.initialize(config);
            let style = '';
            let subStyle = '';
            if (mermaid_scroll_x) {
                style += 'overflow-x: auto;';
            }
            (async () => {
                try {
                    this.$el.html($("<div/>", { id: this.chartId }));
                    const { svg, bindFunctions } = await mermaid.render(this.chartId, this.value);
                    let maxWidth = parseFloat($(svg).css("max-width"));
                    if (maxWidth) {
                        const ratio = parseFloat(division_ration);
                        maxWidth = maxWidth / ratio;
                    }
                    this.$el.find("#" + this.chartId).css("width", maxWidth);
                    this.$el.find("#" + this.chartId).html(svg);
                } catch (e) {
                    this.$el.html($("<pre/>").text(e.message || e.str));
                }
            })();
        },
    });

    field_registry.add("mermaid", MermaidField);

    return {
        MermaidField: MermaidField,
        defaultConfig: defaultConfig,
    };
});
