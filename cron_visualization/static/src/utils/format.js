/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

// The dashboard formats its durations itself rather than with
// `formatFloatTime`, whose output changes across Odoo versions (Odoo 20 turned
// "01:30:05" into "1h 30m"): it needs a stable clock format, to the second.

const pad = (n) => String(n).padStart(2, "0");

function toClock(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

/**
 * Format a number of minutes as HH:MM:SS (hours are not wrapped at 24).
 * Negative values keep their sign; anything that is not a finite number
 * formats as an empty string.
 *
 * @param {number|string|false|null|undefined} minutes
 * @returns {string}
 */
export function formatMinutes(minutes) {
    const value = typeof minutes === "string" ? parseFloat(minutes) : minutes;
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "";
    }
    const totalSeconds = Math.round(Math.abs(value) * 60);
    const sign = value < 0 && totalSeconds > 0 ? "-" : "";
    return `${sign}${toClock(totalSeconds)}`;
}

/**
 * Format a number of minutes as a countdown: "2 days and 03:04:05" from 24
 * hours on, "03:04:05" below. A negative value (an overdue cron) is prefixed
 * with "-".
 *
 * @param {number|false|null|undefined} minutes
 * @returns {string}
 */
export function formatCountdown(minutes) {
    if (typeof minutes !== "number" || !Number.isFinite(minutes)) {
        return "";
    }
    // Round once, on the whole value, so that the day part and the clock part
    // can never disagree (no "0 days and 24:00:00").
    const totalSeconds = Math.round(Math.abs(minutes) * 60);
    const days = Math.floor(totalSeconds / 86400);
    const clock = toClock(totalSeconds % 86400);
    const dayText = days === 1 ? _t("day") : _t("days");
    const dayPart = days > 0 ? `${days} ${dayText} ${_t("and")} ` : "";
    const sign = minutes < 0 && totalSeconds > 0 ? "-" : "";
    return `${sign}${dayPart}${clock}`;
}

/**
 * Parse the "a;b;c,a;b;c" strings the server computes for the dashboard into
 * a list of arrays, ignoring malformed entries.
 *
 * @param {string|false} value
 * @returns {string[][]}
 */
export function parseEntries(value) {
    if (!value || typeof value !== "string") {
        return [];
    }
    return value
        .split(",")
        .filter((item) => item.includes(";"))
        .map((item) => item.split(";"));
}
