import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("remove_discuss_activity_icon_tour", {
    steps: () => [
        {
            content: "Wait for the systray to be rendered",
            trigger: ".o_menu_systray .o_user_menu",
        },
        {
            content: "Neither the Activities nor the Messages icon is in the systray",
            trigger:
                ".o_menu_systray:not(:has([aria-label='Activities'])):not(:has([aria-label='Messages']))",
            run() {
                const systray = registry.category("systray");
                if (systray.contains("mail.activity_menu") || systray.contains("mail.messaging_menu")) {
                    throw new Error("A mail systray entry is still registered");
                }
            },
        },
    ],
});
