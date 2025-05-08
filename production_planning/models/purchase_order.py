from odoo import fields, models, api, Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    planning_id = fields.Many2one(comodel_name='mrp.production.planning',
                                  string='Planning')
    planning_lines_id = fields.Many2one('mrp.production.planning.line')
    is_outsourcing = fields.Boolean(string="Is Outsourcing?", copy=False)
    is_subcontract = fields.Boolean(string="Is Outsourcing?", copy=False)

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for purchase in self:
            if purchase.subcontracting_resupply_picking_count:
                resupply_picks = purchase._get_subcontracting_resupplies()
                for pick in resupply_picks.filtered(lambda pick: pick.state not in ['done', 'cancel']):
                    product_ids = pick.move_ids.mapped("product_id")
                    pick.location_id = product_ids[0].source_location_id.id
                for pick in self.picking_ids.filtered(lambda pick: pick.state not in ['done', 'cancel']):
                    product_ids = pick.move_ids.mapped("product_id")
                    pick.location_dest_id = product_ids[0].destination_location_id.id
        return res

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
