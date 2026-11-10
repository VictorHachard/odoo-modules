import { animationFrame, beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    editSearch,
    fields,
    getFacetTexts,
    models,
    mountView,
    mountWithSearch,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { CUSTOM_SEARCH_GROUP } from "@enhanced_security_search/search_bar/search_bar";

describe.current.tags("desktop");

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    bool = fields.Boolean();
    birthday = fields.Date();
    amount = fields.Float({ aggregator: "sum" });
    country = fields.Selection({
        selection: [
            ["be", "Belgium"],
            ["fr", "France"],
        ],
    });

    _records = [
        { id: 1, name: "A", foo: "x", bool: true, amount: 1, country: "be", birthday: "2026-01-01" },
        { id: 2, name: "B", foo: "y", bool: false, amount: 2, country: "fr", birthday: "2026-02-01" },
    ];
}

defineModels([Partner]);

const SEARCH_ARCH = `
    <search>
        <field name="foo"/>
        <filter name="filter_foo" string="Foo is x" domain="[('foo', '=', 'x')]"/>
        <filter name="birthday" string="Birthday" date="birthday"/>
        <filter name="groupby_bool" string="Bool" context="{'group_by': 'bool'}"/>
    </search>`;

let customSearchAllowed;
let stepGroupChecks;

beforeEach(() => {
    customSearchAllowed = false;
    stepGroupChecks = false;
    const hasGroup = user.hasGroup;
    patchWithCleanup(user, {
        hasGroup(group) {
            if (group === CUSTOM_SEARCH_GROUP) {
                if (stepGroupChecks) {
                    expect.step(`hasGroup ${group}`);
                }
                return Promise.resolve(customSearchAllowed);
            }
            return hasGroup.call(this, group);
        },
    });
});

async function mountSearchBar(params = {}) {
    return mountWithSearch(SearchBar, {
        resModel: "partner",
        searchMenuTypes: ["filter", "groupBy", "favorite"],
        searchViewId: false,
        searchViewArch: SEARCH_ARCH,
        ...params,
    });
}

describe("search panel", () => {
    test("without the group: no custom filter, custom group or save", async () => {
        await mountSearchBar();
        await toggleSearchBarMenu();
        expect(".o_filter_menu .o_menu_item").not.toHaveCount(0);
        expect(".o_filter_menu .o_add_custom_filter").toHaveCount(0);
        expect(".o_add_custom_group_menu").toHaveCount(0);
        expect(".o_add_favorite").toHaveCount(0);
        // The predefined entries are all still there.
        expect(queryAllTexts(".o_filter_menu .o_menu_item")).toEqual(["Foo is x", "Birthday"]);
        expect(queryAllTexts(".o_group_by_menu .o_menu_item")).toEqual(["Bool"]);
    });

    test("without the group: no Custom Date... in a date filter", async () => {
        await mountSearchBar();
        await toggleSearchBarMenu();
        await toggleMenuItem("Birthday");
        expect(".o_filter_menu .o_item_option").not.toHaveCount(0);
        expect(queryAllTexts(".o_filter_menu .dropdown-item")).not.toInclude("Custom Date...");
    });

    test("with the group: every control is offered", async () => {
        customSearchAllowed = true;
        await mountSearchBar();
        await toggleSearchBarMenu();
        expect(".o_filter_menu > .o_add_custom_filter").toHaveCount(1);
        expect(".o_add_custom_group_menu").toHaveCount(1);
        expect(".o_add_favorite").toHaveCount(1);
        await toggleMenuItem("Birthday");
        expect(queryAllTexts(".o_filter_menu .dropdown-item")).toInclude("Custom Date...");
    });

    test("the group is asked once per component, from the session cache", async () => {
        stepGroupChecks = true;
        await mountSearchBar();
        // SearchBar and SearchBarMenu each ask; no RPC is involved.
        expect.verifySteps([`hasGroup ${CUSTOM_SEARCH_GROUP}`, `hasGroup ${CUSTOM_SEARCH_GROUP}`]);
    });

    test("with the group, the view's own hideCustomGroupBy is still honoured", async () => {
        customSearchAllowed = true;
        await mountSearchBar({ hideCustomGroupBy: true });
        await toggleSearchBarMenu();
        expect(".o_add_custom_group_menu").toHaveCount(0);
        expect(".o_filter_menu > .o_add_custom_filter").toHaveCount(1);
    });

    test("predefined filters and group-bys still apply", async () => {
        await mountSearchBar();
        await toggleSearchBarMenu();
        await toggleMenuItem("Foo is x");
        await toggleMenuItem("Bool");
        expect(getFacetTexts()).toEqual(["Foo is x", "Bool"]);
    });
});

describe("search bar", () => {
    test("without the group: a facet does not open the domain editor", async () => {
        await mountSearchBar({ context: { search_default_filter_foo: true } });
        expect(getFacetTexts()).toEqual(["Foo is x"]);
        expect(".o_facet_overlay").toHaveCount(0);
        expect(".o_searchview_facet_label").toHaveAttribute("role", "img");
        await contains(".o_searchview_facet_label").click();
        expect(".modal").toHaveCount(0);
    });

    test("with the group: a facet opens the domain editor", async () => {
        customSearchAllowed = true;
        await mountSearchBar({ context: { search_default_filter_foo: true } });
        expect(".o_facet_overlay").toHaveCount(1);
        expect(".o_searchview_facet_label").toHaveAttribute("role", "button");
        await contains(".o_facet_with_domain .o_searchview_facet_label").click();
        expect(".modal").toHaveCount(1);
        expect(".modal header").toHaveText("Custom Filter");
    });

    test("without the group: the group-by sort toggle keeps working", async () => {
        const searchBar = await mountSearchBar();
        searchBar.env.searchModel.canOrderByCount = true;
        await toggleSearchBarMenu();
        await toggleMenuItem("Bool");
        expect(getFacetTexts()).toEqual(["Bool"]);
        await contains(".o_searchview_facet_label .oi[data-icon='swap_vert']", { visible: false }).click();
        expect(".o_searchview_facet_label .oi[data-icon='arrow_downward']").toHaveCount(1);
        expect(".modal").toHaveCount(0);
    });

    test("without the group: no Custom Filter... in the autocomplete", async () => {
        await mountSearchBar();
        await editSearch("x");
        await animationFrame();
        expect(".o_searchview_autocomplete .o-dropdown-item").not.toHaveCount(0);
        expect(queryAllTexts(".o_searchview_autocomplete .o-dropdown-item")).not.toInclude(
            "Custom Filter..."
        );
    });

    test("with the group: Custom Filter... ends the autocomplete", async () => {
        customSearchAllowed = true;
        await mountSearchBar();
        await editSearch("x");
        await animationFrame();
        expect(".o_searchview_autocomplete .o-dropdown-item:last").toHaveText("Custom Filter...");
    });

    test("without the group: no code path reaches the custom filter dialog", async () => {
        const searchBar = await mountSearchBar();
        searchBar.selectItem({ isAddCustomFilterButton: true });
        await animationFrame();
        expect(".modal").toHaveCount(0);
    });
});

describe("pivot", () => {
    const PIVOT_ARCH = `
        <pivot>
            <field name="country" type="row"/>
            <field name="amount" type="measure"/>
        </pivot>`;

    test("without the group: no Add Custom Group in the header dropdown", async () => {
        await mountView({ type: "pivot", resModel: "partner", arch: PIVOT_ARCH, searchViewArch: SEARCH_ARCH });
        await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
        expect(".o-dropdown--menu").toHaveCount(1);
        expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(0);
        // The predefined group-by is still offered.
        expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toInclude("Bool");
    });

    test("with the group: Add Custom Group in the header dropdown", async () => {
        customSearchAllowed = true;
        await mountView({ type: "pivot", resModel: "partner", arch: PIVOT_ARCH, searchViewArch: SEARCH_ARCH });
        await contains("tbody tr:last-child .o_pivot_header_cell_closed").click();
        expect(".o-dropdown--menu .o_add_custom_group_menu").toHaveCount(1);
    });
});
