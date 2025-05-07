from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    is_edit = fields.Boolean(compute="compute_edit_lot")

    @api.depends('picking_id', 'picking_id.picking_type_id', 'picking_id.picking_type_id.show_operations', 'picking_id.picking_type_id.show_reserved')
    def compute_edit_lot(self):
        for rec in self:
            if rec.picking_id and rec.picking_id.picking_type_id and not rec.picking_id.picking_type_id.show_operations and not rec.picking_id.picking_type_id.show_reserved and rec.picking_id.check_ids and 'open' in rec.picking_id.check_ids.inspection_sheet_id.filtered(lambda x: x.product_id == rec.product_id).mapped('state'):
                rec.is_edit = False
            else:
                rec.is_edit = True
