# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    source_location_id = fields.Many2one('stock.location', 'Default Source Location',
                                         related="product_tmpl_id.source_location_id", readonly=False, store=True)
    destination_location_id = fields.Many2one('stock.location', 'Default Destination Location',
                                              related="product_tmpl_id.destination_location_id", readonly=False,
                                              store=True)
    show_qty_in_pcs = fields.Boolean(string="Show Quantity in PCS", related="product_tmpl_id.show_qty_in_pcs",
                                     readonly=False,
                                     store=True)
    grade_id = fields.Many2one("product.grade", related="product_tmpl_id.grade_id", readonly=False, store=True)
    size = fields.Char(string="Size", related='product_tmpl_id.size', readonly=False, store=True)
    is_raw_material = fields.Boolean(string="Is RawMaterial?", related='product_tmpl_id.is_raw_material',
                                     readonly=False, store=True)
    production_cost = fields.Float(string='Production Cost', related='product_tmpl_id.production_cost', readonly=False, store=True)

    def get_product_destination_location(self):
        return self.destination_location_id or self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id or self.env.company.id)], limit=1).lot_stock_id
