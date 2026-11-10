import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

const TYPES = [
    ["individual", "Individual"],
    ["employee", "Employee"],
    ["company", "Company"],
    ["contact", "Contact"],
    ["invoice", "Invoice Address"],
    ["delivery", "Delivery Address"],
    ["other", "Other Address"],
];

// a stand-alone model: the widget only needs a selection field
class Partner extends models.Model {
    _name = "contacts.icon.test";

    name = fields.Char();
    icon_type_selection = fields.Selection({ selection: TYPES });

    _records = TYPES.map(([value], index) => ({
        id: index + 1,
        name: `Partner ${value}`,
        icon_type_selection: value,
    }));
}

defineMailModels();
defineModels([Partner]);

onRpc("has_group", () => true);

function iconOf(id) {
    return `.o_data_row:nth-child(${id}) .o_partner_icon_type i`;
}

test("simple widget: addresses share the contact icon", async () => {
    await mountView({
        resModel: "contacts.icon.test",
        type: "list",
        arch: `<list><field name="icon_type_selection" widget="partner_icon_type"/><field name="name"/></list>`,
    });
    expect(".o_partner_icon_type i").toHaveCount(TYPES.length);
    expect(iconOf(1)).toHaveClass("fa-male");
    expect(iconOf(2)).toHaveClass("fa-id-badge");
    expect(iconOf(3)).toHaveClass("fa-building");
    for (const id of [4, 5, 6, 7]) {
        expect(iconOf(id)).toHaveClass("fa-address-book");
    }
    expect(iconOf(3)).toHaveAttribute("data-tooltip", "Company");
});

test("detailed widget: one icon per address type", async () => {
    await mountView({
        resModel: "contacts.icon.test",
        type: "list",
        arch: `<list><field name="icon_type_selection" widget="partner_icon_type_all"/><field name="name"/></list>`,
    });
    expect(iconOf(4)).toHaveClass("fa-address-book");
    expect(iconOf(5)).toHaveClass("fa-money");
    expect(iconOf(6)).toHaveClass("fa-truck");
    expect(iconOf(7)).toHaveClass("fa-ellipsis-v");
    expect(iconOf(6)).toHaveAttribute("data-tooltip", "Delivery Address");
});

test("no icon when the value is empty", async () => {
    Partner._records = [{ id: 1, name: "Empty", icon_type_selection: false }];
    await mountView({
        resModel: "contacts.icon.test",
        type: "list",
        arch: `<list><field name="icon_type_selection" widget="partner_icon_type"/><field name="name"/></list>`,
    });
    expect(".o_partner_icon_type").toHaveCount(0);
});
