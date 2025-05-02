from odoo import fields, models, api
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[('packaging', 'Packaging')], ondelete={'packaging': 'set default'})

    @api.constrains('type')
    def _check_is_valid_type(self):
        for rec in self:
            if type == 'packaging' and rec.operation_ids:
                raise UserError("Please remove lines from operation tab!")
