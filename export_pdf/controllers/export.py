# -*- coding: utf-8 -*-
import odoo.http as http
from odoo.addons.web.controllers.main import ExportFormat, Export, serialize_exception
from odoo.http import request


class ExportInherit(Export):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        res = super().formats()
        res += [
            {'tag': 'pdf_landscape', 'label': 'PDF landscape'},
            {'tag': 'pdf_portrait', 'label': 'PDF portrait'}
        ]
        return res


class PdfExport(ExportFormat, http.Controller):

    @http.route(['/web/export/pdf_landscape', '/web/export/pdf_portrait'], type='http', auth="user")
    @serialize_exception
    def index(self, data):
        if '/pdf_landscape' in request.httprequest.path:
            self.format = 'landscape'
        else:
            self.format = 'portrait'
        return self.base(data)

    @property
    def content_type(self):
        return 'application/pdf'

    @property
    def extension(self):
        return '.pdf'

    def from_data(self, fields, rows):
        context = dict(request.context)
        if self.format == 'landscape':
            context |= {"landscape": True}
            
        export_data = {
            'header': fields,
            'data': rows,
        }
        report = request.env['ir.actions.report']._get_report_from_name('export_pdf.export_in_pdf')
        pdf_content = report.with_context(context)._render_qweb_pdf([], data=export_data)

        return pdf_content
