import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });

    _records = [
        { id: 1, name: "Parent" },
        { id: 2, name: "Child", parent_id: 1 },
    ];
}

defineModels([Partner]);

test("many2one_image widget: can open the record in a form view by default", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `<form><field name="parent_id" widget="many2one_image"/></form>`,
    });
    expect(".o_field_many2one_image .o_external_button").toHaveCount(1);
});

test("many2one_image widget: the no_open option is honoured", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `<form><field name="parent_id" widget="many2one_image" options="{'no_open': True}"/></form>`,
    });
    expect(".o_field_many2one_image .o_external_button").toHaveCount(0);
});
