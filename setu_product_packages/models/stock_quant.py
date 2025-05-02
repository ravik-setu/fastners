from odoo import models, fields, api, _
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = "stock.quant"


    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        """
            Author: hetvi.rathod@setuconsulting.com
            Date: 02/04/2024
            purpose: if context get 'exclude_package' then , pass
                        package_id false in package domain and remove lot_id false from domain
        """
        if self.env.context.get('exclude_package') or self.env.context.get('apply_package_domain'):
            domain = [('product_id', '=', product_id.id)]
            if not strict:
                if lot_id:
                    domain = expression.AND([[('lot_id', '=', lot_id.id)], domain])
                if package_id:
                    domain = expression.AND([[('package_id', '=', package_id.id)], domain])
                else:
                    domain = expression.AND([[('package_id', '=',False)], domain])
                if owner_id:
                    domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
                domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
            else:
                domain = expression.AND(
                    [[('lot_id', '=', lot_id.id)] if lot_id else [('lot_id', '=', False)],
                     domain])
                domain = expression.AND([[('package_id', '=', False)], domain])
                domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
                domain = expression.AND([[('location_id', '=', location_id.id)], domain])
            if self.env.context.get('with_expiration'):
                domain = expression.AND(
                    [['|', ('expiration_date', '>=', self.env.context['with_expiration']), ('expiration_date', '=', False)],
                     domain])
            return domain
        return super()._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
