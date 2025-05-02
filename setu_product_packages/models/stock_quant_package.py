from odoo import models, fields, api, _
from odoo.osv import expression


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    main_package_id = fields.Many2one('setu.product.package')
    move_line_ids = fields.One2many('stock.move.line', 'outer_quant_package_id')
    contained_qty = fields.Integer(compute="_compute_contained_qty_weight",store=True)
    net_weight = fields.Float(compute="_compute_contained_qty_weight",store=True)
    total_weight = fields.Float(compute="_compute_contained_qty_weight",store=True)
    weight_uom_name = fields.Char()
    outer_package = fields.Boolean()

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 02/04/2024
             purpose: return packages that are not outer package and quantity greater than 0
        """
        if self.env.context.get('product_id'):
            package_ids = self.get_available_quant_packages()
            if ['id', 'in', []] in domain:
                index = domain.index(['id', 'in', []])
                not_sign_index =  domain.index('!')
                in_operator = 'not in' if not_sign_index +1 ==  index else 'in'
                domain[index] = ['id', in_operator, package_ids._ids]
            else:
                domain = expression.AND([
                    domain,
                    [('id', 'in', package_ids._ids)]
                ])
        return super(StockQuantPackage, self)._name_search(name, domain, operator, limit, order)

    def update_name_based_on_package_type(self):
        sequence = self.env.ref('stock.seq_quant_package')
        if self.package_type_id.prefix:
            name = self.name.replace(sequence.prefix, '')
            self.name = self.package_type_id.prefix + name



    @api.depends('quant_ids.quantity')
    def _compute_contained_qty_weight(self):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 17/04/2024
             purpose: set package quantity and weight if product qty changed in package
             --------------------------------------------------------------------------
             Updated by : ashutosh.pathak@setuconsulting.com
             Date : 21/05/2024 || Task no: 102
             Purpose : Compute package quantity, net weight and toal weight for cases like: (1) inner pkg (2) outer pkg (3) base
        """
        for rec in self:
            quant_ids = rec.quant_ids
            if quant_ids:
                if rec.main_package_id and rec.main_package_id.outer_box:
                    rec.contained_qty = rec.main_package_id.total_qty
                    rec.net_weight = rec.main_package_id.net_weight
                    rec.total_weight = rec.main_package_id.total_weight
                else:
                    net_weight = 0
                    total_weight = 0
                    rec.contained_qty = sum(quant_ids.mapped('quantity'))
                    product_ids = quant_ids.mapped('product_id')
                    for product_id in product_ids:
                        unit_weight = product_id.weight
                        quant = quant_ids.filtered(lambda x:x.product_id == product_id)
                        product_qty = sum(quant.mapped('quantity'))
                        total_product_weight = product_qty * unit_weight
                        net_weight += total_product_weight
                        package_weight = product_id.packaging_ids[0].box_product_id.weight
                        total_weight += net_weight
                        total_weight += package_weight
                    rec.net_weight = net_weight
                    rec.total_weight = total_weight

    def get_available_quant_packages(self):
        product_id = self.env['product.product'].browse(self.env.context.get('product_id'))
        quants = self.env["stock.quant"].search([('product_id', '=', product_id.id),
                                                 ('package_id', '!=', False), ('quantity', '>', 0),
                                                 ('package_id.outer_package', '=', False),
                                                 ('location_id.usage', '=', 'internal')])
        return quants.mapped('package_id')

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if self.env.context.get('product_id'):
            package_ids = self.get_available_quant_packages()
            domain.extend([('id', 'in', package_ids._ids)])
        return super().web_search_read(domain, specification, offset, limit, order, count_limit)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockQuantPackage, self).create(vals_list)
        for rec in res.filtered(lambda pack: pack.package_type_id.prefix):
            rec.update_name_based_on_package_type()
        return res
