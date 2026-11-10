import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor, waitUntil } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    preloadBundle,
} from "@web/../tests/web_test_helpers";

class Flow extends models.Model {
    _name = "flow";

    diagram = fields.Text();
    trigger = fields.Char({
        onChange: (record) => {
            record.diagram = record.trigger ? `graph TB\n${record.trigger}` : false;
        },
    });

    _records = [
        { id: 1, diagram: "graph TB\nA --> B" },
        { id: 2, diagram: false },
        { id: 3, diagram: 'graph TB\nA("#lt;b#gt;bold#quot;") --> B' },
        { id: 4, diagram: "graph TB\nA --> <img src=x onerror=window.__mermaidXss=1>" },
    ];
}

defineModels([Flow]);

preloadBundle("web_widget_mermaid_field.mermaid_lib");

const FORM_ARCH = `
    <form>
        <field name="trigger"/>
        <field name="diagram" widget="mermaid" options="{'mermaid_scroll_x': True, 'division_ration': 2}"/>
    </form>`;

async function mountFlow(resId, arch = FORM_ARCH) {
    await mountView({ type: "form", resModel: "flow", resId, arch });
}

function nodeCount() {
    return document.querySelectorAll(".o_form_field_mermaid svg .node").length;
}

test("renders the diagram as an SVG", async () => {
    await mountFlow(1);
    await waitFor(".o_form_field_mermaid svg");
    expect(nodeCount()).toBe(2);
    expect(".o_form_field_mermaid_error").toHaveCount(0);
});

test("widget options are applied and not given to Mermaid", async () => {
    await mountFlow(1);
    await waitFor(".o_form_field_mermaid svg");
    const chart = queryOne(".o_form_field_mermaid");
    expect(chart.parentElement.getAttribute("style")).toBe("overflow-x: auto;");
    const svgWidth = parseFloat(queryOne(".o_form_field_mermaid svg").style.maxWidth);
    expect(Math.abs(parseFloat(chart.style.width) - svgWidth / 2)).toBeLessThan(0.01);
});

test("an empty value draws nothing", async () => {
    await mountFlow(2);
    expect(".o_form_field_mermaid").toHaveCount(1);
    expect(".o_form_field_mermaid svg").toHaveCount(0);
    expect(".o_form_field_mermaid_error").toHaveCount(0);
});

test("Mermaid entity codes are shown as text, not as markup", async () => {
    await mountFlow(3);
    await waitFor(".o_form_field_mermaid svg");
    expect(".o_form_field_mermaid svg b").toHaveCount(0);
    expect(".o_form_field_mermaid svg .node:first").toHaveText('<b>bold"');
});

test("a syntax error is shown as text", async () => {
    await mountFlow(4);
    await waitFor(".o_form_field_mermaid_error");
    expect(".o_field_widget[name=diagram] img").toHaveCount(0);
    expect(".o_form_field_mermaid_error").toHaveText(/Parse error/);
    expect(window.__mermaidXss).toBe(undefined);
});

test("the diagram follows the value of the record", async () => {
    await mountFlow(2);
    expect(".o_form_field_mermaid svg").toHaveCount(0);

    await contains(".o_field_widget[name=trigger] input").edit("A --> B --> C");
    await waitUntil(() => nodeCount() === 3);
    expect(nodeCount()).toBe(3);

    await contains(".o_field_widget[name=trigger] input").edit("A -->");
    await waitFor(".o_form_field_mermaid_error");
    expect(".o_form_field_mermaid svg").toHaveCount(0);

    await contains(".o_field_widget[name=trigger] input").edit("X --> Y");
    await waitUntil(() => nodeCount() === 2);
    expect(".o_form_field_mermaid_error").toHaveCount(0);

    await contains(".o_field_widget[name=trigger] input").clear();
    await waitUntil(() => nodeCount() === 0);
    expect(".o_form_field_mermaid svg").toHaveCount(0);
});
