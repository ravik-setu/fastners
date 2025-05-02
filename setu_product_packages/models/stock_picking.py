from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    show_create_package = fields.Boolean(related='picking_type_id.show_create_package', store=True)

    def action_picking_create_package(self, is_outer=False):
        """
          Author: hetvi.rathod@setuconsulting.com
          Date: 17/04/2024
          purpose: return product package action
        """
        view_id = self.env.ref("setu_product_packages.setu_product_package_form").id
        return {
            'name': _('Create your Package'),
            'type': 'ir.actions.act_window',
            'res_model': 'setu.product.package',
            'target': 'current',
            'view_mode': 'form',
            'views': [(view_id, "form")],
            'context': {'picking_id': self.id, 'default_outer_box': is_outer},
        }

    def action_create_outer_package(self):
        return self.action_picking_create_package(is_outer=True)
