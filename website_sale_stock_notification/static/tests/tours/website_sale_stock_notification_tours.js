import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_stock_notification.disabled", {
    steps: () => [
        {
            content: "The product is out of stock",
            trigger: "#product_stock_availability #out_of_stock_message",
        },
        {
            content: "Add to cart is hidden and no 'Notify me' button is offered",
            trigger:
                "#o_wsale_cta_wrapper:has(#add_to_cart_wrap.d-none):not(:has(#stock_notification_button)):not(:has(#out_of_stock_buttons_wrapper))",
        },
        {
            content: "No subscription form either",
            trigger: "#product_detail:not(:has(#stock_notification_wrapper))",
        },
    ],
});
