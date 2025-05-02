from odoo import http
from odoo.http import request, content_disposition
import base64


class FileController(http.Controller):
    @http.route('/web/binary/download_final_test_report', type='http', auth="public", website=True)
    def file_template(self, model, field, id, filename=None, **kw):
        file_records = request.env['mrp.production.planning'].browse(id)
        files = []
        fields = [field]
        uid = request.session.uid
        model_obj = request.env[model].with_user(uid)
        res = model_obj.browse(int(id)).read(fields)[0]
        filecontent = base64.b64decode(res.get(field) or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
        return request.make_response(filecontent, headers=[('Content-Type', 'image/png'),
                                                           ('Content-disposition', content_disposition(filename))])
