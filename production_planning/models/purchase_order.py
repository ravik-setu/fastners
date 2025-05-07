from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
