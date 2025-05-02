from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class SetuQualityChecks(models.Model):
    _name = 'setu.quality.checks'
    _description = "Quality Checks"
    _inherit = 'mail.thread'
    _order = 'id desc'

    name = fields.Char(string="Name")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    picking_id = fields.Many2one(comodel_name="stock.picking", string="Picking")
    qc_parameter_id = fields.Many2one(comodel_name="setu.qc.parameters", string="QC Parameter", domain="[('product_id','=',product_id)]")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    note = fields.Html(string="Instructions")
    additional_note = fields.Text(string="Note")
    worksheet_id = fields.Integer(string="Worksheet")
    purchase_id = fields.Many2one(comodel_name="purchase.order", string="Purchase Order")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code('setu.quality.checks.seq')
            vals.update({'name': name})
        res = super(SetuQualityChecks, self).create(vals_list)
        return res


    def open_qc_worksheet(self):
        # move_ids = self.picking_id.move_ids
        # product_wise_move_id = move_ids.filtered(lambda x: x.product_id == self.product_id)
        # lot_id = product_wise_move_id.lot_ids[:1] if product_wise_move_id and len(product_wise_move_id) == 1 else ''
        lot_id = self.dispatch_id.lot_ids.filtered(lambda x: x.product_id == self.product_id and x.company_id == self.company_id and x.name == self.dispatch_id.name)
        dispatch_purchase_order_details_ids = self.dispatch_id.dispatch_purchase_order_details_ids.filtered(lambda x: x.purchase_id == self.purchase_id and x.product_id == self.product_id)
        return {
            'name': 'Worksheet',
            'view_mode': 'form',
            'res_model': self.qc_parameter_id.worksheet_templ_id.model,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.worksheet_id,
            'context': {
                'default_x_partner_id': self.picking_id.partner_id.id,
                'default_x_product_id': self.product_id.id,
                'default_x_company_id': self.company_id.id,
                'default_x_quantity': dispatch_purchase_order_details_ids.dispatch_quantity,
                'default_x_packing_id': dispatch_purchase_order_details_ids.product_packaging_id.id,
                'default_x_lot_id': lot_id.id
            }
        }