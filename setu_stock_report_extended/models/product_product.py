from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    forecast_qty = fields.Float(string='Forecast Quantity', compute='_compute_product_forecast_qty', store=True)

    def action_create_purchase_order(self):
        lines = [(0, 0, {
            'product_id': rec.id,
            'product_qty': 0 if rec.forecast_qty >= 0 else -rec.forecast_qty}) for rec in self]
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'target': 'current',
            'context': {'default_order_line': lines},
        }

    @api.depends('qty_available', 'incoming_qty', 'outgoing_qty')
    def _compute_product_forecast_qty(self):
        for rec in self:
            rec.forecast_qty = rec.qty_available + rec.incoming_qty - rec.outgoing_qty
