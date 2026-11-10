import { registry } from "@web/core/registry";

// Imported so that both entries are registered before they are removed.
import "@mail/core/web/activity_menu";
import "@mail/core/web/messaging_menu_in_dropdown";

const systrayRegistry = registry.category("systray");
systrayRegistry.remove("mail.activity_menu");
systrayRegistry.remove("mail.messaging_menu");
