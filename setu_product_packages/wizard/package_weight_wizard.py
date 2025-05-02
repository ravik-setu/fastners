# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PackageWeightWizard(models.TransientModel):
    """
    This model is created for implement Automate Workstation Flow
    """
    _name = 'package.weight.wizard'
    _description = "Package Weight Wizard"

    package_id = fields.Many2one("setu.product.package")
    weight = fields.Float(string="Weight", digits=(4, 4))
    setu_weight = fields.Html()

    def do_weight_and_update_in_package(self):
        if type(self.weight) != float:
            raise UserError('Weight Should be in float')
        weight = self.weight or self.setu_weight
        if weight < self.package_id.min_weight or weight > self.package_id.max_weight:
            raise UserError(
                "Package Weight should between {} to {}".format(self.package_id.min_weight, self.package_id.max_weight))
        line_id = self.env["setu.package.line"].create(
            {'package_id': self.package_id.id, 'weight': weight,
             'quant_package_id': self.package_id.create_quant_package().id,
             'lot_ids': [(4, self.env.context.get("package_lot_id"))]})
        # attachment = line_id.action_generate_label(line_id)
        # return attachment

    @api.model
    def update_weight_in_wizard(self, *args, **kwargs):
        try:
            wizard = self.browse(args[0])
            wizard.write({'weight': args[1]})
        except Exception as e:
            _logger.error("Error: {}, Comes at the time of updating weight {} in wizard".format(e, args[1]))
            return False
        return True
