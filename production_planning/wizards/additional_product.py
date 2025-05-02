from odoo import models, api, fields
from odoo.exceptions import UserError
import base64



class MrpWorkorderAdditionalProduct(models.TransientModel):
    _name = "mrp_workorder.additional.product"

    product_id = fields.Many2one(
        'product.product',
        'Product',
        required=True,
        domain="[('company_id', 'in', (company_id, False)), ('type', '!=', 'service')]")
    product_tracking = fields.Selection(related='product_id.tracking')
    product_qty = fields.Float('Quantity', default=1, required=True)
    product_uom_id = fields.Many2one('uom.uom', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    type = fields.Selection([
        ('component', 'Component'),
        ('byproduct', 'By-Product')])
    production_id = fields.Many2one(
        'mrp.production', required=True,
        default=lambda self: self.env.context.get('production_id', None))
    workorder_id = fields.Many2one('mrp.workorder')
    company_id = fields.Many2one(related='production_id.company_id')
    lot_id = fields.Many2one("stock.lot", string="Lot/Serial Number")
    is_return = fields.Boolean("Is Return?")

    def add_product(self):
        """
        Added By : Ravi Kotadiya | On : Aug-21-2023
        Use : To create internal transfer from RM to WIP and reserve product into related MO
        """
        picking_obj = self.env["stock.picking"]
        production_id = self.workorder_id.production_id or self.production_id
        production_id.raise_error_if_multiple_lot_found(self.lot_id)
        location_id = self.product_id.is_raw_material and self.product_id.destination_location_id or production_id.location_src_id
        available_qty = self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=self.lot_id,
                                                                        strict=True)
        if available_qty < self.product_qty:
            raise UserError(
                "You are trying to add more quantity then available\nAvailable: {},\nAdd: {}".format(available_qty,
                                                                                                     self.product_qty))
        if not production_id.is_src_contain_wip_stock_location:
            picking_obj.do_unreserve_and_reserve_based_on_lot(move_ids=production_id.move_raw_ids, lot_ids=self.lot_id,
                                                              avoid_unreserve=True, qty=self.product_qty)
        production_id.create_internal_transfer(self.product_id, self.product_qty, self.lot_id)
        picking_obj.do_unreserve_and_reserve_based_on_lot(move_ids=production_id.move_raw_ids, lot_ids=self.lot_id,
                                                          avoid_unreserve=True, qty=self.product_qty)
        raw_material_movement_id = production_id.create_raw_material_movement(self.product_id, self.product_qty,
                                                               production_id.location_src_id,
                                                               production_id.location_dest_id, lot_id=self.lot_id)
        attachment = raw_material_movement_id._generate_label()
        return attachment

    def return_product(self):
        """
        Added By : Ravi Kotadiya | On : Aug-21-2023
        Use : To create internal transfer from wip to Rm
        """
        production_id = self.workorder_id.production_id or self.production_id
        if not production_id.is_src_contain_wip_stock_location:
            return True
        max_return_qty = sum(
            self.env['mrp.production.planning'].get_available_qty_on_location(self.product_id,
                                                                              production_id.location_src_id,
                                                                              find_quant=True).mapped('quantity'))
        if production_id.state not in ['done', 'cancel']:
            production_id.move_raw_ids._do_unreserve()
        if max_return_qty < self.product_qty:
            raise UserError("Sorry you can only move {}{} to raw material stock!".format(max_return_qty,
                                                                                        self.product_id.uom_id.name))
        production_id.create_internal_transfer(self.product_id, self.product_qty, self.lot_id, is_return=True)
        raw_material_movement_id = production_id.create_raw_material_movement(self.product_id, self.product_qty,
                                                   production_id.location_dest_id, production_id.location_src_id, self.lot_id
                                                  )
        label_action = raw_material_movement_id._generate_label()
        return label_action

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            if self.product_tracking == 'serial':
                self.product_qty = 1
