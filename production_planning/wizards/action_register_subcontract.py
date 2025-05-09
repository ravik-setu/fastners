from odoo import fields, models, api
from odoo.exceptions import UserError


class RegisterSubcontract(models.Model):
    _name = 'register.subcontract'
    _description = 'Register Daily Subcontract'

    partner_id = fields.Many2one('res.partner', string='Subcontractor')
    planning_id = fields.Many2one("mrp.production.planning")
    planning_line = fields.Many2one("mrp.production.planning.line")
    workorder_id = fields.Many2one("mrp.workorder")
    subcontract_qty = fields.Float("Subcontract Qty")
    product_id = fields.Many2one("product.product", related="planning_line.product_id", string="Product")
    bom_id = fields.Many2one('mrp.bom')

    def register_subcontract(self):
        subcontractor_id = self.bom_id.subcontractor_ids and self.bom_id.subcontractor_ids[-1]
        if subcontractor_id and self.subcontract_qty > 0:
            purchase_id = self.env['purchase.order'].prepare_vals_and_create_purchase_order(vendor_id=subcontractor_id,
                                                                              product_id=self.product_id,
                                                                              product_uom_id=self.product_id.uom_id,
                                                                              product_qty=self.subcontract_qty,
                                                                              planning_id=self.planning_id,
                                                                              planning_line_id=self.planning_line)
            if hasattr(purchase_id, 'is_outsourcing'):
                purchase_id.is_outsourcing = True
            self.planning_line.write({'subcontract_bom_id': self.bom_id})
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'res_id': purchase_id.id,
                'target': 'current',
            }
        return False
