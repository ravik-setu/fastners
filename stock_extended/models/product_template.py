# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    source_location_id = fields.Many2one('stock.location', 'Default Source Location', tracking=True)
    destination_location_id = fields.Many2one('stock.location', 'Default Destination Location', tracking=True)
    show_qty_in_pcs = fields.Boolean(string="Show Quantity in PCS")
    grade_id = fields.Many2one("product.grade")
    size = fields.Char(string="Size")
    is_raw_material = fields.Boolean(string="Is RawMaterial?")
    detailed_type = fields.Selection(default='product')
    production_cost = fields.Float(string='Production Cost')
