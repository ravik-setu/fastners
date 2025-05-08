from odoo import fields, models, api
from odoo.osv import expression


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """
        Author: Ishani Manvar || Date: 08/05/2025
        Purpose: To show only those lots that are available in source location.
        """
        if self.env.context.get('component') and self.env.context.get('production_id'):
            product_id = self.env['product.product'].search([('id', '=', self.env.context.get('component'))])
            production_id = self.env['mrp.production'].search([('id', '=', self.env.context.get('production_id'))])
            location_id = product_id.is_raw_material and product_id.destination_location_id or production_id.location_src_id
            quant_ids = self.env['stock.quant'].search([('product_id', '=', product_id.id),
                                                        ('location_id', '=', location_id.id), ('quantity', '>', 0)])
            domain = expression.AND([
                domain,
                [('id', 'in', quant_ids.lot_id.ids)]
            ])
        return super(StockLot, self)._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """
        Author: Ishani Manvar || Date: 08/05/2025
        Purpose: To show only those lots that are available in source location.
        """
        if self.env.context.get('component') and self.env.context.get('production_id'):
            product_id = self.env['product.product'].search([('id', '=', self.env.context.get('component'))])
            production_id = self.env['mrp.production'].search([('id', '=', self.env.context.get('production_id'))])
            location_id = product_id.is_raw_material and product_id.destination_location_id or production_id.location_src_id
            quant_ids = self.env['stock.quant'].search([('product_id', '=', product_id.id),
                                                        ('location_id', '=', location_id.id), ('quantity', '>', 0)])
            domain = expression.AND([
                domain,
                [('id', 'in', quant_ids.lot_id.ids)]
            ])
        return super(StockLot, self).web_search_read(domain, specification, offset, limit, order, count_limit)
