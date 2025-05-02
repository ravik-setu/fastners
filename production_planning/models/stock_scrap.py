from odoo import fields, models, api
from odoo.exceptions import UserError

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def action_validate(self, lot_id):
        if self.scrap_qty and self.production_id.state != 'done':
            production_reserved_qty = sum(self.production_id.move_raw_ids.mapped('quantity'))
            lot_ids = self.production_id.move_raw_ids.move_line_ids.mapped('lot_id')
            if production_reserved_qty < self.scrap_qty:
                raise UserError("Sorry you can not scrap more then {}{}!".format(production_reserved_qty,
                                                                                 self.product_id.uom_id.name))
            self.env["stock.picking"].do_unreserve_and_reserve_based_on_lot(self.production_id.move_raw_ids, lot_ids,
                                                                            qty=production_reserved_qty - self.scrap_qty)
            self.production_id.create_raw_material_movement(self.product_id, self.scrap_qty, self.location_id, lot_id,
                                                            self.scrap_location_id)
        return super(StockScrap, self).action_validate()
