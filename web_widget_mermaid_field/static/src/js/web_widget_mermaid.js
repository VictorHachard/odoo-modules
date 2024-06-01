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
            var config = _.extend({}, defaultConfig, this.attrs.options);
            mermaid.initialize(config);
            (async () => {
                try {
                    this.$el.html($("<div/>", { id: this.chartId }));
                    const { svg, bindFunctions } = await mermaid.render(this.chartId, this.value);
                    //const maxWidth = parseFloat($(svg).css("max-width")) / 1.5;
                    //this.$el.find("#" + this.chartId).css("width", maxWidth);
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
