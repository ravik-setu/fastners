from odoo import fields, models, api
from odoo.exceptions import UserError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_wip_stock_location = fields.Boolean("IS WIP Stock Location?")

    @api.constrains('is_wip_stock_location', 'valuation_in_account_id', 'valuation_out_account_id')
    def _check_location_contains_valuation(self):
        for rec in self:
            if rec.is_wip_stock_location and not rec.valuation_in_account_id:
                raise UserError(
                    "Stock Valuation Account(Incoming) is not set into location {}".format(rec.display_name))
            if rec.is_wip_stock_location and not rec.valuation_out_account_id:
                raise UserError(
                    "Stock Valuation Account(Outgoing) is not set into location {}".format(rec.display_name))
