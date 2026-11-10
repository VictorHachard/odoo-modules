import { defineBusModels, waitForChannels } from "@bus/../tests/bus_test_helpers";
import { advanceTime, animationFrame, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    MockServer,
    mountView,
    mountWebClient,
    onRpc,
    patchTranslations,
} from "@web/../tests/web_test_helpers";

import { getTickWatchers } from "@cron_visualization/cron_float_time_day/cron_float_time_day";
import { formatCountdown, formatMinutes, parseEntries } from "@cron_visualization/utils/format";

describe.current.tags("desktop");

const CHANNEL = "cron_visualization.dashboard";
const NOTIFICATION = "cron_history_update";

class IrCron extends models.Model {
    _name = "ir.cron";

    name = fields.Char();
    interval_number = fields.Integer();
    cv_is_running = fields.Boolean();
    cv_next_execution_timer = fields.Float();
    cv_history = fields.Char();
    cv_progress_estimated = fields.Char();

    _views = { kanban: KANBAN_ARCH };

    _records = [
        {
            id: 1,
            name: "Mail queue",
            interval_number: 1,
            cv_is_running: true,
            cv_next_execution_timer: 90.5,
            cv_history: "success;1.5,fail;0.25,interruption;,running;",
            cv_progress_estimated: "50.0;5.0;automatic,;1.0;manual",
        },
        {
            id: 2,
            name: "Autovacuum",
            interval_number: 1,
            cv_is_running: false,
            cv_next_execution_timer: 1500,
            cv_history: "",
            cv_progress_estimated: false,
        },
        {
            id: 3,
            name: "Overdue",
            interval_number: 1,
            cv_is_running: false,
            cv_next_execution_timer: -10,
            cv_history: false,
            cv_progress_estimated: false,
        },
    ];
}

class CvIrCronHistory extends models.Model {
    _name = "cv.ir.cron.history";

    type = fields.Selection({
        selection: [
            ["manual", "Manual"],
            ["automatic", "Automatic"],
        ],
    });
    state = fields.Char();

    _views = { list: `<list><field name="state"/></list>` };

    _records = [
        { id: 1, type: "manual", state: "success" },
        { id: 2, type: "automatic", state: "fail" },
        { id: 3, type: false, state: "running" },
    ];
}

defineBusModels();
defineModels([IrCron, CvIrCronHistory]);

const KANBAN_ARCH = `
    <kanban js_class="ir_cron_kanban">
        <templates>
            <t t-name="card">
                <field name="name"/>
                <field name="cv_is_running" widget="spinner_widget"/>
                <field name="cv_next_execution_timer" widget="cron_float_time_day_widget"/>
                <field name="cv_history" widget="cron_history_widget"/>
                <field name="cv_progress_estimated" widget="cron_progressbar_widget"/>
            </t>
        </templates>
    </kanban>`;

function card(index) {
    return queryAll(".o_kanban_record:not(.o_kanban_ghost)")[index];
}

async function mountDashboard() {
    await mountView({ type: "kanban", resModel: "ir.cron", arch: KANBAN_ARCH });
}

describe("format helpers", () => {
    test("formatMinutes renders a clock and keeps the sign", () => {
        expect(formatMinutes(0)).toBe("00:00:00");
        expect(formatMinutes(1.5)).toBe("00:01:30");
        expect(formatMinutes(0.25)).toBe("00:00:15");
        expect(formatMinutes(90.5)).toBe("01:30:30");
        // Hours are not wrapped at 24: a 30 hour run reads 30 hours.
        expect(formatMinutes(1800)).toBe("30:00:00");
        expect(formatMinutes(-10)).toBe("-00:10:00");
        expect(formatMinutes("2.5")).toBe("00:02:30");
        // Rounding carries over instead of printing 60 seconds.
        expect(formatMinutes(59.9999)).toBe("01:00:00");
    });

    test("formatMinutes ignores what is not a number", () => {
        for (const value of ["", "None", undefined, null, false, NaN, Infinity]) {
            expect(formatMinutes(value)).toBe("");
        }
    });

    test("formatCountdown adds the days", () => {
        patchTranslations();
        expect(formatCountdown(0)).toBe("00:00:00");
        expect(formatCountdown(90.5)).toBe("01:30:30");
        expect(formatCountdown(1440)).toBe("1 day and 00:00:00");
        expect(formatCountdown(1500)).toBe("1 day and 01:00:00");
        expect(formatCountdown(3 * 1440 + 61)).toBe("3 days and 01:01:00");
        expect(formatCountdown(-10)).toBe("-00:10:00");
        expect(formatCountdown(-1500)).toBe("-1 day and 01:00:00");
        // Never "0 days and 24:00:00" one fraction of a second before a day.
        expect(formatCountdown(1439.99999)).toBe("1 day and 00:00:00");
        // No negative zero.
        expect(formatCountdown(-0.000001)).toBe("00:00:00");
        expect(formatCountdown(false)).toBe("");
    });

    test("parseEntries drops malformed entries", () => {
        expect(parseEntries(false)).toEqual([]);
        expect(parseEntries("")).toEqual([]);
        expect(parseEntries("success;1.0,garbage,fail;2")).toEqual([
            ["success", "1.0"],
            ["fail", "2"],
        ]);
        expect(parseEntries(";5.0;manual")).toEqual([["", "5.0", "manual"]]);
    });
});

describe("dashboard widgets", () => {
    test("history widget draws one dot per run, with the duration as tooltip", async () => {
        await mountDashboard();
        const dots = queryAll(".cv_history_dot", { root: card(0) });
        expect(dots.map((dot) => [...dot.classList].find((c) => c.startsWith("bg-")))).toEqual([
            "bg-success",
            "bg-danger",
            "bg-warning",
            "bg-primary",
        ]);
        expect(dots[0]).toHaveAttribute("data-tooltip", "00:01:30");
        expect(dots[1]).toHaveAttribute("data-tooltip", "00:00:15");
        expect(dots[2]).not.toHaveAttribute("data-tooltip");
        expect(queryAll(".cv_history_dot", { root: card(1) })).toHaveLength(0);
        expect(queryAll(".cv_history_dot", { root: card(2) })).toHaveLength(0);
    });

    test("progress bar: a percentage when estimated, indeterminate otherwise", async () => {
        await mountDashboard();
        const rows = queryAll(".o_cron_progress", { root: card(0) });
        expect(rows).toHaveLength(2);

        const known = queryOne(".progress-bar", { root: rows[0] });
        expect(known).toHaveText("50%");
        expect(known).toHaveAttribute("aria-valuenow", "50");
        expect(known.getAttribute("style")).toInclude("50%");
        expect(queryOne(".oi", { root: rows[0] })).toHaveAttribute("data-icon", "flash_on");
        expect(queryOne(".text-nowrap", { root: rows[0] })).toHaveText("00:05:00");

        const unknown = queryOne(".progress-bar", { root: rows[1] });
        expect(unknown).toHaveClass("o_cron_progress_unknown");
        expect(unknown).toHaveText("");
        expect(queryOne(".oi", { root: rows[1] })).toHaveAttribute("data-icon", "person");
        expect(queryOne(".text-nowrap", { root: rows[1] })).toHaveText("00:01:00");
    });

    test("progress bar placeholder when the cron is idle", async () => {
        await mountDashboard();
        expect(queryAll(".o_cron_progress", { root: card(1) })).toHaveLength(0);
        expect(queryAll(".progress", { root: card(1) })).toHaveLength(1);
        expect(queryAll(".progress-bar", { root: card(1) })).toHaveLength(0);
    });

    test("spinner shows whether the cron is running", async () => {
        await mountDashboard();
        expect(queryOne(".spinner-border", { root: card(0) })).toHaveClass("text-success");
        expect(queryOne(".spinner-border", { root: card(0) })).toHaveAttribute("data-tooltip", "Running");
        expect(queryOne(".spinner-border", { root: card(1) })).toHaveClass("text-warning");
        expect(queryOne(".spinner-border", { root: card(1) })).toHaveAttribute("data-tooltip", "Stopped");
    });

    test("next execution countdown ticks every second", async () => {
        await mountDashboard();
        const countdown = (index) =>
            queryOne(".o_field_cron_float_time_day_widget", { root: card(index) });
        expect(countdown(0)).toHaveText("01:30:30");
        expect(countdown(1)).toHaveText("1 day and 01:00:00");
        expect(countdown(2)).toHaveText("-00:10:00");

        await advanceTime(5000);
        await animationFrame();
        expect(countdown(0)).toHaveText("01:30:25");
        // Overdue crons count up.
        expect(countdown(2)).toHaveText("-00:10:05");
    });

    test("every countdown shares a single timer", async () => {
        const before = getTickWatchers();
        await mountDashboard();
        expect(getTickWatchers()).toBe(before + 3);
    });

    test("type widget shows who started the run", async () => {
        await mountView({
            type: "list",
            resModel: "cv.ir.cron.history",
            arch: `<list><field name="type" widget="cron_type_widget"/><field name="state"/></list>`,
        });
        const icons = queryAll(".o_field_cron_type_widget");
        expect(icons).toHaveLength(3);
        expect(queryOne(".oi", { root: icons[0] })).toHaveAttribute("data-icon", "person");
        expect(queryOne(".oi", { root: icons[0] })).toHaveAttribute("data-tooltip", "Manual");
        expect(queryOne(".oi", { root: icons[1] })).toHaveAttribute("data-icon", "flash_on");
        expect(queryOne(".oi", { root: icons[1] })).toHaveAttribute("data-tooltip", "Automatic");
        expect(queryAll(".oi", { root: icons[2] })).toHaveLength(0);
    });
});

describe("live dashboard", () => {
    test("kanban renderer gets the full-width class", async () => {
        await mountDashboard();
        expect(".o_kanban_renderer").toHaveClass("ir_cron_kanban_style");
        expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(3);
        expect(card(0)).toHaveText(/^Mail queue/);
        expect(card(1)).toHaveText(/^Autovacuum/);
    });

    test("listens on the dashboard channel and reloads on notification", async () => {
        onRpc("ir.cron", "web_search_read", () => {
            expect.step("reload");
        });
        await mountDashboard();
        await waitForChannels([CHANNEL]);
        expect.verifySteps(["reload"]);

        MockServer.env["ir.cron"].write([1], { name: "Mail queue (renamed)" });
        // A burst of notifications is debounced into one reload.
        MockServer.env["bus.bus"]._sendone(CHANNEL, NOTIFICATION, { cron_ids: [1] });
        MockServer.env["bus.bus"]._sendone(CHANNEL, NOTIFICATION, { cron_ids: [1] });
        await expect.waitForSteps(["reload"]);
        await animationFrame();
        expect(card(0)).toHaveText(/Mail queue \(renamed\)/);
        // Debounced: the burst gave a single reload.
        await advanceTime(1000);
        expect.verifySteps([]);
    });

    test("other notification types do not reload", async () => {
        onRpc("ir.cron", "web_search_read", () => {
            expect.step("reload");
        });
        await mountDashboard();
        await waitForChannels([CHANNEL]);
        expect.verifySteps(["reload"]);
        MockServer.env["bus.bus"]._sendone(CHANNEL, "something_else", {});
        // A notification of ours sent afterwards proves the first one was
        // delivered and ignored, rather than simply not delivered yet.
        MockServer.env["bus.bus"]._sendone(CHANNEL, NOTIFICATION, { cron_ids: [2] });
        await expect.waitForSteps(["reload"]);
        await advanceTime(1000);
        expect.verifySteps([]);
    });

    test("leaving the dashboard drops the channel", async () => {
        defineActions([
            {
                id: 1,
                name: "Scheduled Actions",
                res_model: "ir.cron",
                type: "ir.actions.act_window",
                views: [[false, "kanban"]],
            },
            {
                id: 2,
                name: "History",
                res_model: "cv.ir.cron.history",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        ]);
        await mountWebClient();
        await getService("action").doAction(1);
        await waitForChannels([CHANNEL]);
        await getService("action").doAction(2, { clearBreadcrumbs: true });
        await waitForChannels([CHANNEL], { operation: "delete" });
    });
});
