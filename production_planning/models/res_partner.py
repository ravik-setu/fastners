from odoo import fields, models, api
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    code = fields.Char(string="Code")

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """
        """
        if self.env.context.get('subc_bom_id'):
            bom_id = self.env['mrp.bom'].search([('id', '=', self.env.context.get('subc_bom_id'))])
            domain = expression.AND([
                domain,
                [('id', 'in', bom_id.subcontractor_ids.ids)]
            ])
        return super(ResPartner, self)._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if self.env.context.get('subc_bom_id'):
            bom_id = self.env['mrp.bom'].search([('id', '=', self.env.context.get('subc_bom_id'))])
            domain = expression.AND([
                domain,
                [('id', 'in', bom_id.subcontractor_ids.ids)]
            ])
        return super(ResPartner, self).web_search_read(domain, specification, offset, limit, order, count_limit)
