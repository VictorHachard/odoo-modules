import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Flow extends models.Model {
    _name = "flow";

    diagram = fields.Text();

    _records = [
        { id: 1, diagram: "graph TB\nA --> B" },
        { id: 2, diagram: "graph TB\nA --> <img src=x onerror=window.__mermaidXss=1>" },
    ];
}

defineModels([Flow]);

async function mountFlow(resId) {
    await mountView({
        type: "form",
        resModel: "flow",
        resId,
        arch: `<form><field name="diagram" widget="mermaid"/></form>`,
    });
}

test("mermaid widget: renders the diagram as an SVG", async () => {
    await mountFlow(1);
    await waitFor(".o_form_field_mermaid svg", { timeout: 5000 });
    expect(".o_form_field_mermaid_error").toHaveCount(0);
});

test("mermaid widget: a syntax error is shown as text", async () => {
    await mountFlow(2);
    await waitFor(".o_form_field_mermaid_error", { timeout: 5000 });
    expect(".o_field_widget[name=diagram] img").toHaveCount(0);
    expect(".o_form_field_mermaid_error").toHaveText(/Parse error/);
    expect(window.__mermaidXss).toBe(undefined);
});
