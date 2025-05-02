from odoo import fields, models, api
import base64

class SetuRawMaterialMovement(models.Model):
    _name = 'setu.raw.material.movement'
    _description = 'Raw Material Movement'

    production_id = fields.Many2one("mrp.production")
    product_id = fields.Many2one("product.product")
    quantity = fields.Float()
    location_id = fields.Many2one("stock.location")
    location_dest_id = fields.Many2one("stock.location")
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")

    def _generate_label(self):
        param = self.env['ir.config_parameter'].sudo().get_param('production_planning.print_label', default='False')
        if param:
            report = self.env.ref('production_planning.action_component_product_label_report')
            pdf_content, _ = report.sudo()._render_qweb_pdf('production_planning.action_component_product_label_report',
                                                            self.id)

            attachment = self.env['ir.attachment'].create({
                'name': f"Label_{self.id}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'close_add_product_wizard',
                'params': {
                    'url': '/web/content/%s?download=true' % attachment.id,
                }
            }
        return False
