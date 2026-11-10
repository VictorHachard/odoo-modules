import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class History extends models.Model {
    _name = "ier.template.action.history";

    manifest = fields.Text();

    _records = [
        {
            id: 1,
            manifest: JSON.stringify({
                ir_exports: [
                    { name: "Tags", model_name: "res.partner.category", fields: ["id", "name"] },
                    { name: "Countries", model_name: "res.country", fields: ["id"] },
                ],
            }),
        },
        { id: 2, manifest: "not json" },
        { id: 3, manifest: false },
    ];
}

defineModels([History]);

onRpc("has_group", () => true);

const ARCH = `<form><field name="manifest" widget="ier_manifest"/></form>`;

test("renders one row per export with its fields", async () => {
    await mountView({ resModel: "ier.template.action.history", type: "form", resId: 1, arch: ARCH });
    expect(".ier_manifest_widget tr").toHaveCount(3);
    expect(".ier_manifest_widget tr:nth-child(2) td:first-child").toHaveText("Tags");
    expect(".ier_manifest_widget tr:nth-child(2) .ier_badge").toHaveCount(2);
    expect(".ier_manifest_widget tr:nth-child(3) td:nth-child(2)").toHaveText("res.country");
});

test("renders nothing for an invalid manifest", async () => {
    await mountView({ resModel: "ier.template.action.history", type: "form", resId: 2, arch: ARCH });
    expect(".ier_manifest_widget").toHaveCount(0);
});

test("renders nothing for an empty manifest", async () => {
    await mountView({ resModel: "ier.template.action.history", type: "form", resId: 3, arch: ARCH });
    expect(".ier_manifest_widget").toHaveCount(0);
});
