from odoo import fields, models, api


class ProductGrade(models.Model):
    _name = 'product.grade'
    _description = 'Product Grade'

    name = fields.Char()
