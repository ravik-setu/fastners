from odoo import fields, models, api


class QualityCharacteristic(models.Model):
    _name = 'setu.quality.characteristic'
    _inherit = ['mail.thread']
    _description = 'QualityCharacteristic'

    name = fields.Char(compute='_generate_name')
    code = fields.Char(tracking=True)
    description = fields.Char(tracking=True)
    active = fields.Boolean(default=True,tracking=True)

    @api.depends('code', 'description')
    def _generate_name(self):
        for rec in self:
            rec.name = "%s %s" % (rec.code or '', rec.description or '')