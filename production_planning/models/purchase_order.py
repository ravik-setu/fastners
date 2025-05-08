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
                resupply_picks = purchase._get_subcontracting_resupplies().filtered(
                    lambda pick: pick.state not in ['done', 'cancel'])
                pickings = self.picking_ids.filtered(lambda pick: pick.state not in ['done', 'cancel'])
                for line in purchase.order_line:
                    if line.product_id.source_location_id:
                        line_resupply = resupply_picks.group_id.mrp_production_ids.filtered(
                            lambda mo: mo.product_id.id == line.product_id.id).picking_ids
                        line_resupply.location_id = line.product_id.source_location_id.id
                    if line.product_id.destination_location_id:
                        pickings.filtered(lambda
                                              pick: pick.product_id.id == line.product_id.id).location_dest_id = line.product_id.destination_location_id.id
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
