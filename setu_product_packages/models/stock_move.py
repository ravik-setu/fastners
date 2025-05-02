from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, OrderedSet

class StockMove(models.Model):
    _inherit = "stock.move"

    product_package_move_id = fields.Many2one('setu.product.package')

    def _action_done(self, cancel_backorder=False):
        """
        Author: Ishani Manvar
        Purpose: To automatically create a package of the product quantity that is manufactured.
        """
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        moves_to_pack = self.filtered(
            lambda m: m.product_id == m.production_id.product_id and m.state == 'done' and m.product_id.auto_package)
        for move in moves_to_pack:
            if move.picking_type_id.auto_package:
                if self.product_id.packaging_ids and self.product_id.packaging_ids[:1].qty:
                    move._create_setu_package(move.production_id.lot_producing_id, move.location_dest_id)
        return res

    def _create_setu_package(self, lot_ids, location_id):
        """
        Author: Ishani Manvar
        Purpose: To make packages of equal size for the quantity that is manufactured.
        """
        if (self.product_uom_qty % self.product_id.packaging_ids[:1].qty):
            raise UserError(
                _("Please enter the quantity to be manufactured in a multiple of the package size."))
        qty_to_be_produced = self.product_uom_qty
        package_size = self.product_id.packaging_ids[:1].qty
        total_packages = qty_to_be_produced / package_size
        setu_package_vals = {'package_state': 'draft',
                             'outer_box': False,
                             'outer_box_type': self.product_id.packaging_ids[:1].package_type_id.id,
                             'source_location_id': location_id.id,
                             'package_ids': [(0, 0, {
                                 'product_id': self.product_id.id,
                                 'product_package_id': self.product_id.packaging_ids[:1].id,
                                 'package_qty': total_packages,
                                 'lot_ids': [(6, 0, lot_ids.ids)],
                             })]}
        setu_package_id = self.env['setu.product.package'].create(setu_package_vals)
        setu_package_id.create_package()

    def reserve_based_on_package(self, package_ids):
        """
            Author: hetvi.rathod@setuconsulting.com
            Date: 17/04/2024
            purpose: assign created package in move line ids of picking moves
        """
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in self.filtered(lambda m: (m.product_uom_qty - m.quantity) > 0):
            package_ids = package_ids.mapped('quant_ids').filtered(
                lambda quant: quant.product_id == move.product_id and quant.available_quantity).mapped('package_id')
            lot_ids = package_ids.mapped('quant_ids').mapped('lot_id')
            need = move.product_uom_qty - move.quantity
            if not need:
                continue
            move.reserved_qty_from_package(package_ids, need, lot_ids, assigned_moves_ids,
                                           partially_available_moves_ids)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    def reserved_qty_from_package(self, package_ids, need, lot_ids, assigned_moves_ids,
                                  partially_available_moves_ids):
        """
        Updated By : Ravi Kotadiya | On : Oct-07-2024 | Task : 1003
        Use : To reserve move qty from packages
        """
        for package in package_ids:
            if not need:
                return
            if self.product_id.tracking != 'none':
                for lot_id in lot_ids:
                    if need:
                        need = self.get_available_and_reserve(need, lot_id, package, assigned_moves_ids,
                                                              partially_available_moves_ids)
            else:
                if need:
                    need = self.get_available_and_reserve(need, False, package, assigned_moves_ids,
                                                          partially_available_moves_ids)
        return need

    def get_available_and_reserve(self, need, lot_id, package, assigned_moves_ids, partially_available_moves_ids):
        """
        Updated By : Ravi Kotadiya | On : Oct-07-2024 | Task : 1003
        Use : Find available qty and reserve
        """
        available_quantity = self._get_available_quantity(self.location_id, lot_id=lot_id,
                                                          package_id=package, strict=True)
        if float_is_zero(available_quantity, precision_rounding=self.product_uom.rounding):
            return need
        taken_quantity = self._update_reserved_quantity(min(need, available_quantity),
                                                        location_id=self.location_id,
                                                        lot_id=lot_id, package_id=package, strict=True)
        if float_is_zero(taken_quantity, precision_rounding=self.product_uom.rounding):
            return need
        if float_is_zero(need - taken_quantity, precision_rounding=self.product_uom.rounding):
            assigned_moves_ids.add(self.id)
            return need - taken_quantity
        need -= taken_quantity
        partially_available_moves_ids.add(self.id)
        return need
