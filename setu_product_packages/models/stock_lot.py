from pydoc import browse

from odoo import fields, models, api
from odoo.osv import expression


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 02/04/2024
             purpose: return lots that have available stock
        """
        location = self.env["stock.location"]
        product_obj = self.env["product.product"]
        if self.env.context.get('product_id') and self.env.context.get('location_id'):
            product_id = product_obj.browse(self.env.context.get('product_id'))
            exclude = dict(self._context)
            location = location.browse(self.env.context.get('location_id'))
            exclude.update({'exclude_package': True})
            quants = self.env["stock.quant"].with_context(exclude)._gather(product_id, location)
            quants = quants.filtered(lambda quant: quant.available_quantity and not quant.package_id)
            domain = expression.AND([
                domain,
                [('id', 'in', quants.mapped('lot_id')._ids)]
            ])
        return super(StockLot, self)._name_search(name, domain, operator, limit, order)