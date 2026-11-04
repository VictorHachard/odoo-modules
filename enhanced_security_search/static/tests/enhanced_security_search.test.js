import { animationFrame, beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    editSearch,
    fields,
    getFacetTexts,
    models,
    mountWithSearch,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { user } from "@web/core/user";
import { SearchBar } from "@web/search/search_bar/search_bar";

describe.current.tags("desktop");

const GROUP = "enhanced_security_search.group_custom_search";

class Partner extends models.Model {
    foo = fields.Char();
    bool = fields.Boolean();

    _records = [
        { id: 1, foo: "x", bool: true },
        { id: 2, foo: "y", bool: false },
    ];
}

defineModels([Partner]);

const SEARCH_ARCH = `
    <search>
        <field name="foo"/>
        <filter name="filter_foo" string="Foo is x" domain="[('foo', '=', 'x')]"/>
        <filter name="groupby_bool" string="Bool" context="{'group_by': 'bool'}"/>
    </search>`;

let customSearchAllowed;

beforeEach(() => {
    customSearchAllowed = false;
    const hasGroup = user.hasGroup;
    patchWithCleanup(user, {
        hasGroup(group) {
            if (group === GROUP) {
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

test("enhanced_security_search: without the group a facet does not open the domain editor", async () => {
    await mountSearchBar({ context: { search_default_filter_foo: true } });
    expect(getFacetTexts()).toEqual(["Foo is x"]);
    expect(".o_searchview_facet_label .fa-pencil").toHaveCount(0);
    expect(".o_searchview_facet_label").toHaveAttribute("role", "img");
    await contains(".o_searchview_facet_label").click();
    expect(".modal").toHaveCount(0);
});

test("enhanced_security_search: with the group a facet opens the domain editor", async () => {
    customSearchAllowed = true;
    await mountSearchBar({ context: { search_default_filter_foo: true } });
    expect(".o_searchview_facet_label").toHaveAttribute("role", "button");
    await contains(".o_facet_with_domain .o_searchview_facet_label").click();
    expect(".modal").toHaveCount(1);
});

test("enhanced_security_search: without the group the group-by sort toggle keeps working", async () => {
    const searchBar = await mountSearchBar();
    searchBar.env.searchModel.canOrderByCount = true;
    await toggleSearchBarMenu();
    await toggleMenuItem("Bool");
    expect(getFacetTexts()).toEqual(["Bool"]);
    expect(searchBar.env.searchModel.orderByCount).toBe(false);
    await contains(".o_searchview_facet_label").click();
    expect(searchBar.env.searchModel.orderByCount).toBe("Desc");
    expect(".modal").toHaveCount(0);
});

test("enhanced_security_search: without the group no Custom Filter... in the autocomplete", async () => {
    const searchBar = await mountSearchBar();
    await editSearch("x");
    await animationFrame();
    expect(".o_searchview_autocomplete .o-dropdown-item").not.toHaveCount(0);
    expect(queryAllTexts(".o_searchview_autocomplete .o-dropdown-item")).not.toInclude(
        "Custom Filter..."
    );
    searchBar.selectItem({ isAddCustomFilterButton: true });
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test("enhanced_security_search: with the group Custom Filter... is in the autocomplete", async () => {
    customSearchAllowed = true;
    await mountSearchBar();
    await editSearch("x");
    await animationFrame();
    expect(".o_searchview_autocomplete .o-dropdown-item:last").toHaveText("Custom Filter...");
});
