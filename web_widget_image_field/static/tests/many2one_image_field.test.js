import { expect, test } from "@odoo/hoot";
import {
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Task extends models.Model {
    _name = "task";

    product_id = fields.Many2one({ string: "Product", relation: "product" });

    _records = [
        { id: 1, product_id: 1 },
        { id: 2, product_id: false },
    ];
}

class Product extends models.Model {
    _name = "product";

    name = fields.Char();

    _records = [
        { id: 1, name: "Chair", write_date: "2023-02-13 10:00:00" },
        { id: 2, name: "Table", write_date: "2023-02-13 10:00:00" },
    ];
}

defineModels([Task, Product]);

onRpc("has_group", () => true);

const UNIQUE = "unique=1676282400000";

test.tags("desktop");
test("shows the default image of the related record", async () => {
    await mountView({
        type: "form",
        resModel: "task",
        resId: 1,
        arch: `<form><field name="product_id" widget="many2one_image"/></form>`,
    });
    expect(".o_field_many2one_image").toHaveCount(1);
    expect(".o_field_widget[name=product_id] input").toHaveValue("Chair");
    expect(`.o_m2o_avatar > img[data-src="/web/image/product/1/image_128?${UNIQUE}"]`).toHaveCount(1);
    expect(".o_field_many2one_image > div").toHaveAttribute("data-tooltip", "Chair");
    expect(".o_external_button").toHaveCount(1);
});

test.tags("desktop");
test("image_field option and record change", async () => {
    await mountView({
        type: "form",
        resModel: "task",
        resId: 1,
        arch: `<form><field name="product_id" widget="many2one_image" options="{'image_field': 'image_512'}"/></form>`,
    });
    expect(`.o_m2o_avatar > img[data-src="/web/image/product/1/image_512?${UNIQUE}"]`).toHaveCount(1);

    await clickFieldDropdown("product_id");
    await clickFieldDropdownItem("product_id", "Table");
    expect(`.o_m2o_avatar > img[data-src="/web/image/product/2/image_512?${UNIQUE}"]`).toHaveCount(1);
    await clickSave();
    expect(".o_field_widget[name=product_id] input").toHaveValue("Table");
});

test.tags("desktop");
test("no image without value", async () => {
    await mountView({
        type: "form",
        resModel: "task",
        resId: 2,
        arch: `<form><field name="product_id" widget="many2one_image"/></form>`,
    });
    expect(".o_m2o_avatar > img").toHaveCount(0);
    expect(".o_field_widget[name=product_id] input").toHaveValue("");
});

test.tags("desktop");
test("no_open is honoured in form views", async () => {
    await mountView({
        type: "form",
        resModel: "task",
        resId: 1,
        arch: `<form><field name="product_id" widget="many2one_image" options="{'no_open': True}"/></form>`,
    });
    expect(".o_external_button").toHaveCount(0);
});

test("readonly in a list view", async () => {
    await mountView({
        type: "list",
        resModel: "task",
        arch: `<list><field name="product_id" widget="many2one_image"/></list>`,
    });
    expect(".o_data_row:eq(0) .o_m2o_avatar > img").toHaveCount(1);
    expect(".o_data_row:eq(0) .o_field_many2one_image").toHaveText("Chair");
    expect(".o_data_row:eq(1) .o_m2o_avatar > img").toHaveCount(0);
});
