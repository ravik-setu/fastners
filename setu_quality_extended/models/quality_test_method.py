from odoo import fields, models, api


class QualityTestMethod(models.Model):
    _name = "setu.quality.test.method"
    _description = "Quality Test Method"

    name = fields.Char(string="Test Method")
