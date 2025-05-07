from odoo import fields, models, api


class QualityAlertNew(models.Model):
    _inherit = "setu.quality.alert"

    source = fields.Char(string="Source")
