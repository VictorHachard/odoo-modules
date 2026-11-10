# Odoo modules by HVG Solutions

[![Tests](https://github.com/VictorHachard/odoo-modules/actions/workflows/tests.yml/badge.svg?branch=20.0)](https://github.com/VictorHachard/odoo-modules/actions/workflows/tests.yml)

Community modules for Odoo 20.0, developed and maintained by
[HVG Solutions](https://hvg-solutions.com). One branch per Odoo series.

| Module | What it does |
|---|---|
| `base_recompute_field` | Recompute a stored computed field from its technical form (administrators only). |
| `contacts_icon_plus` | Contact type icons and filters (individual, company, employee, contact). |
| `enhanced_security_search` | Hides custom filters, custom group by and saved searches from users outside a group. |
| `import_export_records` | Export and import records across several models with templates. |
| `purchase_stock_flowchart` | Mermaid flowchart of the stock moves of a purchase order. |
| `remove_discuss_activity_icon` | Removes the Discuss and Activity icons from the systray. |
| `res_country_active` | Archive the countries you do not use. |
| `sale_stock_flowchart` | Mermaid flowchart of the stock moves of a sale order. |
| `stock_flowchart` | Technical base of the flowcharts: picking and backorder graph. |
| `tree_style_border_center` | Column borders and centred headers in list views. |
| `web_widget_image_field` | `many2one_image` widget: an image next to a relational field. |
| `web_widget_mermaid_field` | `mermaid` widget: render a text field as a Mermaid diagram. |
| `website_sale_breadcrumb_name` | Custom "All products" label in the shop breadcrumb, per website. |
| `website_sale_stock_notification` | Turn the back-in-stock notification on or off per product. |

## Tests

Every push and pull request on `20.0` runs `.github/workflows/tests.yml`:
a lint of the manifests and files, then each module installed alone on its own
database with its Python and Hoot tests, then all modules together.

Locally, from the folder holding `odoo-20/` and this repository:

```bash
# Git Bash rewrites "/module" into a Windows path without this.
export MSYS_NO_PATHCONV=1
python odoo-modules-20/.github/scripts/lint.py
venv-20/Scripts/python odoo-20/odoo-bin -c odoo-20.conf -d test_mymodule \
    -i mymodule --test-enable --test-tags=/mymodule --stop-after-init
```

## Support

Issues: [GitHub](https://github.com/VictorHachard/odoo-modules/issues).
Custom development and Odoo projects: [hvg-solutions.com](https://hvg-solutions.com),
contact@hvg-solutions.com.
