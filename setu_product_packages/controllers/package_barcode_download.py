from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools import pdf


class FileControllers(http.Controller):

    def _get_barcode_pdfs(self, barcode_type, package_id):
        """
        Author: Ishani Manvar
        Purpose: Returns the barcode pdfs of packages.
        """
        barcode_pdfs = []
        if 'package' in barcode_type:
            setu_package_ids = request.env['stock.quant.package'].search([('main_package_id', '=', int(package_id))])
            package_types_pdf, _content_type = request.env['ir.actions.report']._render_qweb_pdf('stock.report_package_barcode_small', setu_package_ids._ids)
            if package_types_pdf:
                barcode_pdfs.append(package_types_pdf)

        return barcode_pdfs

    @http.route(['/binary/package_barcodes'], type="http", auth="public")
    def file_template(self, id, filename=None):
        """
        Author: Ishani Manvar
        Purpose: Returns the combined barcode pdf of all packages.
        """
        barcode_pdfs = self._get_barcode_pdfs(barcode_type='package', package_id=id)
        if not barcode_pdfs:
            raise UserError(_("Barcodes are not available."))
        merged_pdf = pdf.merge_pdf(barcode_pdfs)
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf))
        ]
        return request.make_response(merged_pdf, headers=pdfhttpheaders)
