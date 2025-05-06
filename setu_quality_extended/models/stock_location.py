from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError

class StockLocation(models.Model):
    _inherit = 'stock.location'

    destructive_location = fields.Boolean('Is a Desctructive Location?')
    reject_location = fields.Boolean('Is a Reject Location?')
    warehouse1_id = fields.Many2one(related="warehouse_id", store=True)

    @api.onchange('destructive_location', 'reject_location')
    def _check_one(self):
        if self.destructive_location:
            if len(self.env['stock.location'].search([('warehouse1_id', '=', self.warehouse1_id.id), ('destructive_location', '=', True)])):
                self.destructive_location = False
                raise ValidationError(
                    _("""Can not have more than one destructive location"""))
        if self.reject_location:
            if len(self.env['stock.location'].search([('warehouse1_id', '=', self.warehouse1_id.id), ('reject_location', '=', True)])):
                self.reject_location = False
                raise ValidationError(
                    _("""Can not have more than one Reject location"""))
