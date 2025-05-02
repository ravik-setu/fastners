from odoo import fields, models, api, Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    planning_id = fields.Many2one(comodel_name='mrp.production.planning',
                                  string='Planning')
    planning_lines_id = fields.Many2one('mrp.production.planning.line')
    is_outsourcing = fields.Boolean(string="Is Outsourcing?", copy=False)
    is_subcontract = fields.Boolean(string="Is Outsourcing?", copy=False)

    def prepare_vals_and_create_purchase_order(self, vendor_id, product_id, product_uom_id, product_qty,
                                               planning_id=False, planning_line_id=False):
        """
        """
        vals = {
            'partner_id': vendor_id.id,
            'order_line': [Command.create({'product_id': product_id.id,
                                           'product_uom': product_uom_id.id,
                                           'product_qty': product_qty})],
            'planning_id': (planning_id and planning_id.id) or planning_id,
            'planning_lines_id': planning_line_id and planning_line_id.id
        }
        return self.create(vals)
