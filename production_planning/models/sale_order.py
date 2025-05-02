from pydoc import browse

from odoo import fields, models, api
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        extra_domain = self.prepare_extra_domain()
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return super(SaleOrder, self)._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        extra_domain = self.prepare_extra_domain()
        if extra_domain:
            domain.extend(extra_domain)
        return super().web_search_read(domain, specification, offset, limit, order, count_limit)

    def prepare_extra_domain(self):
        extra_domain = []
        if self.env.context.get('product_id'):
            extra_domain.append(('order_line.product_id', 'in', [self.env.context.get('product_id')]))
        if self.env.context.get("customer_id"):
            extra_domain.append(('partner_id', '=', self.env.context.get("customer_id")))
        return extra_domain