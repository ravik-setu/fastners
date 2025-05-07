from odoo import models, fields, api


class SetuOuterPackageLine(models.Model):
    _name = 'setu.outer.package.line'
    _description = 'Setu Outer Package Line'

    product_id = fields.Many2one('product.product')
    outer_package_id = fields.Many2one('setu.product.package')
    product_package_ids = fields.Many2many('stock.quant.package','setu_product_packages')
    company_id = fields.Many2one(comodel_name="res.company", default=lambda self: self.env.company)
    package_count = fields.Float(string="Total", compute='_compute_package_count', store=True)

    @api.depends('product_package_ids')
    def _compute_package_count(self):
        for rec in self:
            rec.package_count = len(rec.product_package_ids)
