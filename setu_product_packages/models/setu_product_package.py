from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, OrderedSet
import logging
from odoo.tests import Form

_logger = logging.getLogger(__name__)


class SetuProductPackage(models.Model):
    _name = 'setu.product.package'
    _order = 'id desc'
    _inherit = ['barcodes.barcode_events_mixin']
    _description = 'Setu Product Package'

    name = fields.Char(string='Package Reference', copy=False, required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('setu.product.package.seq'))
    source_location_id = fields.Many2one('stock.location')
    inner_package_line_ids = fields.One2many('setu.package.line', 'package_id')
    setu_package_ids = fields.One2many("stock.quant.package", "main_package_id", string="Packages")
    package_state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', copy=False)
    outer_box = fields.Boolean()
    outer_package_line_ids = fields.One2many('setu.outer.package.line', 'outer_package_id')
    product_moves_ids = fields.One2many('stock.move', 'product_package_move_id')
    outer_box_type = fields.Many2one('stock.package.type')
    plastic_weight = fields.Float(string="Plastic Weight")
    total_qty = fields.Float(string="Total Qty", compute="_compute_total_weight_qty", store=True)
    total_weight = fields.Float(string="Gross Weight",
                                help="Weight of products including packages weight and plastic weight if it is outer-box",
                                compute="_compute_total_weight_qty", store=True)
    net_weight = fields.Float(string="Net Weight", help="Weight of products excluding packages weight",
                              compute="_compute_total_weight_qty", store=True)
    current_scanning_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Current scanning location",
        copy=False
    )
    current_scanning_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Current scanning product",
        copy=False
    )
    current_scanning_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Current scanning lot/serial number",
        copy=False
    )
    current_package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        string="Current Package Type",
        copy=False
    )
    company_id = fields.Many2one(comodel_name="res.company", required=True, default=lambda self: self.env.company)
    package_count = fields.Float(string="Total Box", compute='_compute_package_count', store=True)
    inner_package_type = fields.Selection([('regular', 'Regular'), ('convert_and_pack', 'Convert And Pack')])
    packaging_id = fields.Many2one('product.packaging', string="Package")
    min_weight = fields.Float(string="Min Weight", digits=(4, 4))
    max_weight = fields.Float(string="Max Weight", digits=(4, 4))
    product_id = fields.Many2one('product.product', string="Product")
    put_in_pack_product_id = fields.Many2one('product.product', related="product_id.put_in_pack_product_id")
    product_tracking = fields.Selection(related='put_in_pack_product_id.tracking')
    lot_id = fields.Many2one("stock.lot", string="Lot")

    def create_package(self):
        """
          Author: hetvi.rathod@setuconsulting.com
          Date: 01/04/2024
          purpose: create package for given product and lots and done moves
        """
        move_ids = self.env['stock.move']
        if self.inner_package_type == 'convert_and_pack':
            self.convert_product_and_create_packages()
        else:
            for package in self.inner_package_line_ids:
                domain = [('product_id', '=', package.product_id.id),
                          ('quantity', '>', 0),
                          ('location_id', '=', self.source_location_id.id),
                          ('package_id', '=', False)]
                if package.product_id.tracking == 'lot':
                    domain.append(('lot_id', 'in', package.lot_ids.ids))
                quant = self.env['stock.quant'].search(domain)
                available_quantity = sum(quant.mapped('available_quantity'))
                package_qty = package.package_qty
                product_qty = package.product_package_id.qty
                total_qty = package_qty * product_qty
                package_product = package.product_id
                package_product_weight = package_product.weight
                box_product_weight = 0

                if package.product_id.type == 'product' and available_quantity < total_qty:
                    product_name = package.product_id.name
                    lot_details = " , ".join(package.lot_ids.mapped("name"))
                    _logger.info("You don't have sufficient quantity. Product : {} Lot : {}, Pack Qty : {}, "
                                 "Available Qty : {}".format(product_name, lot_details, package.product_package_id.qty,
                                                             available_quantity))
                    raise UserError(_("You don't have sufficient quantity. \n Product : {}"
                                      "\n Lot : {},\n Pack Qty : {},\n Available Qty : {}".format(product_name,
                                                                                                  lot_details,
                                                                                                  package.product_package_id.qty,
                                                                                                  available_quantity)))

                if package.product_package_id.box_product_id:
                    if package.product_package_id.box_product_id.type == 'product':
                        box_product_quant = self.env['stock.quant'].search(
                            [('product_id', '=', package.product_package_id.box_product_id.id),
                             ('quantity', '>', 0),
                             ('location_id', '=', self.source_location_id.id),
                             ('package_id', '=', False)])
                        box_product_qty = sum(box_product_quant.mapped('available_quantity'))
                        if box_product_qty < package_qty:
                            msg = ("You don't have sufficient quantity. \n Product : {} "
                                   "\nRequired Qty : {}, \nAvailable Qty : {}").format(
                                package.product_package_id.box_product_id.display_name,
                                package_qty,
                                box_product_qty)
                            _logger.info(msg)
                            raise UserError(_(msg))
                    move_id = self.create_box_product_move(package)
                    box_product_weight += package.product_package_id.box_product_id.weight
                    self.write({
                        'product_moves_ids': [(4, move_id.id)]})
                    move_ids += move_id

                for i in range(int(package_qty)):
                    move_id = self.create_package_move(package_product, product_qty)
                    if package.lot_ids:
                        self.set_reserve_based_on_lots(move_id, package.lot_ids)
                    else:
                        exclude = dict(move_id._context)
                        exclude.update({'exclude_package': True})
                        move_id.with_context(exclude)._update_reserved_quantity(product_qty, move_id.location_id,
                                                                                strict=True)

                    move_id._set_quantity_done(move_id.quantity)
                    move_id.picked = True
                    move_line_ids = move_id.move_line_ids
                    move_line_ids = self.package_move_line_vals(move_line_ids)
                    main_package = move_id.picking_id._put_in_pack(move_line_ids)
                    main_package.write(
                        {'package_type_id': package.product_package_id.package_type_id.id,
                         'contained_qty': product_qty})
                    main_package.update_name_based_on_package_type()
                    main_package.net_weight = product_qty * package_product_weight
                    main_package.total_weight = (product_qty * package_product_weight) + box_product_weight
                    _logger.info('package {} total weight is {}'.format(main_package.name,
                                                                        main_package.total_weight))
                    main_package.weight_uom_name = package_product.weight_uom_name
                    self.write({
                        'setu_package_ids': [(4, main_package.id)],
                        'product_moves_ids': [(4, move_id.id)]
                    })
                    move_ids += move_id
            move_ids._action_done()
        if self.setu_package_ids:
            self.package_state = "done"
            if self._context.get('picking_id'):
                self.attach_package_in_picking()
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': _("Packages Created Successfull!"),
                }
            }

    def set_reserve_based_on_lots(self, move_ids, lot_ids):
        """
            Author: hetvi.rathod@setuconsulting.com
            Date: 01/04/2024
            purpose: reserved quantity based on available quantity
        """
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in move_ids:
            need = move.product_qty
            for lot_id in lot_ids:
                if not need:
                    continue
                exclude = dict(move._context)
                exclude.update({'exclude_package': True})
                available_quantity = move.with_context(exclude)._get_available_quantity(move.location_id, lot_id=lot_id,
                                                                                        strict=True)
                if float_is_zero(available_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                taken_quantity = move.with_context(exclude)._update_reserved_quantity(min(need, available_quantity),
                                                                                      location_id=move.location_id,
                                                                                      lot_id=lot_id, strict=True)
                if float_is_zero(taken_quantity, precision_rounding=move.product_uom.rounding):
                    continue
                if float_is_zero(need - taken_quantity, precision_rounding=move.product_uom.rounding):
                    assigned_moves_ids.add(move.id)
                    break
                need -= taken_quantity
                partially_available_moves_ids.add(move.id)
        StockMove = self.env["stock.move"]
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    def create_package_move(self, product, qty, dest_loc=False):
        """
                Author: hetvi.rathod@setuconsulting.com
                Date: 01/04/2024
                purpose: create moves for package
        """

        move_vals = {
            'name': 'created package',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'company_id': self.source_location_id.company_id.id,
            'state': 'confirmed',
            'location_id': self.source_location_id.id,
            'location_dest_id': dest_loc.id if dest_loc else self.source_location_id.id,
            'product_uom_qty': qty,
            'move_line_ids': [(0, 0, {'product_id': product.id,
                                      'location_id': self.source_location_id.id,
                                      'location_dest_id': dest_loc.id if dest_loc else self.source_location_id.id,
                                      })],
        }
        move_id = self.env['stock.move'].create(move_vals)
        return move_id

    def package_move_line_vals(self, move_line_ids):
        """
          Author: hetvi.rathod@setuconsulting.com
          Date: 01/04/2024
          purpose: filter move lines
        """
        quantity_move_line_ids = move_line_ids.filtered(
            lambda ml:
            float_compare(ml.quantity, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0 and
            not ml.result_package_id
        )
        move_line_ids = quantity_move_line_ids.filtered(lambda ml: ml.picked)
        if not move_line_ids:
            move_line_ids = quantity_move_line_ids
        return move_line_ids

    def action_see_created_packages(self):
        """
               Author: hetvi.rathod@setuconsulting.com
               Date: 01/04/2024
               purpose: open view to see created packages
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_package_view")
        packages = self.setu_package_ids.ids
        action['domain'] = [('id', 'in', packages)]
        return action

    def create_box_product_move(self, package):
        """
          Author: hetvi.rathod@setuconsulting.com
          Date: 02/04/2024
          purpose: create move for box product
        """
        package_qty = package.package_qty
        dest_location = self.env['stock.location'].search(
            [('usage', '=', 'production'), ('company_id', '=', self.source_location_id.company_id.id)])
        move_id = self.create_package_move(package.product_package_id.box_product_id, package_qty,
                                           dest_location)
        move_id._update_reserved_quantity(package_qty, move_id.location_id, strict=True)
        move_id._set_quantity_done(move_id.quantity)
        move_id.picked = True
        return move_id

    def put_in_outer_package(self):
        """
           Author: hetvi.rathod@setuconsulting.com
           Date: 02/04/2024
           purpose: return package that have quantity
        """
        move_ids = self.env['stock.move']
        total_weight = 0
        for package in self.outer_package_line_ids:
            product_id = package.product_id
            location_id = self.source_location_id
            product_package_ids = package.product_package_ids
            product_packages_weight = sum(package.product_package_ids.mapped('total_weight'))
            total_weight += product_packages_weight
            quant_ids = product_package_ids.mapped('quant_ids')

            quant_qty = sum(quant_ids.mapped('quantity'))
            move_id = self.create_package_move(product_id, quant_qty)
            for pack in product_package_ids:

                for quant in quant_ids:
                    qty = quant.quantity
                    move_id._update_reserved_quantity(qty, location_id, lot_id=quant.lot_id, package_id=pack)
            self.write({
                'product_moves_ids': [(4, move_id.id)]})
            move_id._set_quantity_done(move_id.quantity)
            move_id.picked = True
            move_ids += move_id

        move_line_ids = move_ids.mapped('move_line_ids')
        move_line_ids = self.package_move_line_vals(move_line_ids)
        # there will be no picking_id in any moves
        main_package = move_ids.mapped('picking_id')._put_in_pack(move_line_ids)
        main_package.write({'package_type_id': self.outer_box_type.id, 'outer_package': True,
                            'move_line_ids': [[6, 0, move_line_ids.ids]]})
        main_package.update_name_based_on_package_type()

        if main_package and self.outer_box:
            if  self.outer_box_type.package_product_id:
                move_id = self.create_outer_box_product_move()
                self.write({
                    'product_moves_ids': [(4, move_id.id)]})
                move_ids += move_id
            outer_box_weight = self.outer_box_type.package_product_id.weight
            main_package.net_weight = total_weight
            total_weight += outer_box_weight
            main_package.total_weight = total_weight

            _logger.info('package {} total weight is {}'.format(main_package.name, main_package.total_weight))

            main_package.weight_uom_name = self.outer_box_type.package_product_id.weight_uom_name
            main_package.contained_qty = sum(
                self.outer_package_line_ids.mapped('product_package_ids').mapped('contained_qty'))
        move_ids._action_done()
        self.write({
            'setu_package_ids': [(4, main_package.id)]})
        if self.setu_package_ids:
            self.package_state = "done"
            if self._context.get('picking_id'):
                self.attach_package_in_picking()
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': _("Packages Created Successfull!"),
                }
            }
        self.current_scanning_product_id = False
        self.current_package_type_id = False
        self.current_scanning_lot_id = False
        self.current_scanning_location_id = False

    def create_outer_box_product_move(self):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 03/04/2024
             purpose: create move for outer box product
        """
        outer_package_qty = 1
        outer_package_product = self.outer_box_type.package_product_id
        if not outer_package_product:
            raise UserError(_('Product is not set in outer box {}'.format(self.outer_box_type.name)))

        outer_product_quant = self.env['stock.quant'].search(
            [('product_id', '=', outer_package_product.id),
             ('quantity', '>', 0),
             ('location_id', '=', self.source_location_id.id),
             ('package_id', '=', False)])
        # box_product_qty = sum(outer_product_quant.mapped('quantity'))
        outer_product_qty = sum(outer_product_quant.mapped('available_quantity'))
        if outer_product_qty < 1:
            _logger.info("You don't have sufficient quantity of {}".format(outer_package_product.name))
            raise UserError(_("You don't have sufficient quantity of {}".format(outer_package_product.name)))

        dest_location = self.env['stock.location'].search(
            [('usage', '=', 'production'), ('company_id', '=', self.source_location_id.company_id.id)])
        move_id = self.create_package_move(outer_package_product, outer_package_qty,
                                           dest_location)

        move_id._update_reserved_quantity(outer_package_qty, move_id.location_id, strict=True)
        move_id._set_quantity_done(move_id.quantity)
        move_id.picked = True
        return move_id

    def action_see_product_moves(self):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 03/04/2024
             purpose: open view to see created product move lines
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_line_action")
        product_move = self.product_moves_ids.ids
        action['domain'] = [('move_id', 'in', product_move)]
        return action

    @api.depends('outer_box_type', 'plastic_weight', 'inner_package_line_ids.product_id',
                 'inner_package_line_ids.package_qty',
                 'outer_package_line_ids.product_package_ids')
    def _compute_total_weight_qty(self):
        """
        Added By : Ravi Kotadiya | On : Apr-15-2024
        Use : To calculate package total weight and show it on the package screen
        :return:
        """
        for rec in self:
            total_qty = 0
            total_weight = 0
            net_weight = 0
            if rec.outer_box_type:
                for line in rec.outer_package_line_ids:
                    total_qty += (sum(line.product_package_ids.mapped('contained_qty')))
                    total_weight += (sum(line.product_package_ids.mapped('total_weight')))
                    net_weight += (sum(line.product_package_ids.mapped('total_weight')))
                total_weight += (rec.outer_box_type.package_product_id.weight + rec.plastic_weight)
            elif not rec.outer_box_type and rec.inner_package_line_ids:
                for line in rec.inner_package_line_ids:
                    qty, weight = self._calculate_package_weight_and_qty(line, line.package_qty)
                    total_qty += qty
                    total_weight += weight
                    net_weight += (line.product_id.weight * line.product_package_id.qty) * line.package_qty
            rec.total_qty = total_qty
            rec.total_weight = total_weight
            rec.net_weight = max(net_weight, 0)

    def _calculate_package_weight_and_qty(self, package_id, qty):
        """
        Added By : Ravi Kotadiya | On : Apr-15-2024
        Use : To get calculate total weight and qty of number of boxes
        :return:
        """
        package_qty = (package_id.product_package_id.qty * qty)
        package_weight = (package_id.product_id.weight * package_qty) + (
                package_id.product_package_id.box_product_id.weight * qty)
        return package_qty, package_weight

    def attach_package_in_picking(self):
        """
             Author: hetvi.rathod@setuconsulting.com
             Date: 17/04/2024
             purpose: pass move ids of picking to assign package
        """
        picking_id = self.env['stock.picking'].browse(self._context.get('picking_id'))
        picking_id.move_ids.reserve_based_on_package(self.setu_package_ids)

    def on_barcode_scanned(self, barcode):
        """
            Author: kishan@setuconsulting
            Date: 12/04/24
            Purpose: create package lines with barcode
        """
        self.ensure_one()
        package_state = self.package_state
        if package_state == 'draft':
            location = self.env['stock.location'].sudo().search([('barcode', '=ilike', barcode)], limit=1)
            if location and not self.source_location_id:
                self.source_location_id = location.id
                self.current_scanning_location_id = location.id
            if self.source_location_id and not self.current_scanning_location_id:
                self.current_scanning_location_id = self.source_location_id.id
            if not self.source_location_id:
                return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'title': _("Warning"),
                    'message': _(
                        "Please scan location first"),
                })
        if package_state == 'draft' and not self.outer_box:
            packages_line = self.inner_package_line_ids

            product = self.env['product.product'].sudo().search([('barcode', '=ilike', barcode)], limit=1)
            package_type = self.env['stock.package.type'].search([('barcode', '=ilike', barcode)], limit=1)
            lot_ids = self.env['stock.lot'].sudo().search([('name', '=ilike', barcode)])
            if package_type:
                if not self.current_scanning_product_id:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please scan product first to product lot."),
                    })
                package_type_in_product_id = self.current_scanning_product_id.packaging_ids.filtered(lambda
                                                                                                         x: x.package_type_id.id == package_type.id and x.product_id.id == self.current_scanning_product_id.id)
                if not package_type_in_product_id:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please configure packaging with current scanned package type in current scanned product."),
                    })
                packages_line_with_current_product_id = packages_line.filtered(
                    lambda x: x.product_id.id == self.current_scanning_product_id.id)
                if not packages_line_with_current_product_id:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please scan product first to scan packaging type."),
                    })
                if packages_line_with_current_product_id:
                    packages_line_with_package_type_and_current_product_id = packages_line_with_current_product_id.filtered(
                        lambda x: x.product_package_id.package_type_id.id == package_type.id)
                    if not packages_line_with_package_type_and_current_product_id:
                        packages_line_with_current_product_id = packages_line_with_current_product_id.filtered(
                            lambda x: not x.product_package_id)
                        if packages_line_with_current_product_id:
                            packages_line_with_current_product_id.product_package_id = package_type_in_product_id.id
                        else:
                            vals = {
                                'product_id': self.current_scanning_product_id.id,
                                'product_package_id': package_type_in_product_id.id
                            }
                            self.write({
                                'inner_package_line_ids': [(0, 0, vals)]
                            })
                    self.current_package_type_id = package_type.id
            if lot_ids and packages_line:
                if not self.current_scanning_product_id or not self.current_package_type_id:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please scan product or package type first to scan lot."),
                    })
                lot_id = lot_ids.filtered(lambda x: x.product_id == self.current_scanning_product_id)
                if not lot_id:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please select an appropriate lot number as current lot is not belongs to the product you have scanned."),
                    })
                packages_line_with_lot_product_id = packages_line.filtered(
                    lambda
                        x: x.product_id.id == lot_id.product_id.id and x.product_package_id.package_type_id.id == self.current_package_type_id.id)
                if packages_line_with_lot_product_id:
                    if lot_id.id not in packages_line_with_lot_product_id.lot_ids.ids:
                        packages_line_with_lot_product_id.write({
                            'lot_ids': [(4, lot_id.id)]
                        })
            if product:
                if self.current_scanning_product_id and self.current_scanning_product_id != product:
                    self.current_scanning_product_id = product.id
                    self.current_scanning_lot_id = False
                    self.current_package_type_id = False
                if packages_line:
                    vals = {}
                    packages_line_with_current_product_id = packages_line.filtered(
                        lambda x: x.product_id.id == product.id)
                    if self.current_package_type_id and packages_line_with_current_product_id:
                        packages_line_with_package_type_and_current_product_id = packages_line_with_current_product_id.filtered(
                            lambda
                                x: x.product_package_id.package_type_id.id == self.current_package_type_id.id and x.product_id.id == product.id)
                        if packages_line_with_package_type_and_current_product_id:
                            if product.tracking in (
                                    'lot',
                                    'serial') and not packages_line_with_package_type_and_current_product_id.lot_ids:
                                return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                    'title': _("Warning"),
                                    'message': _(
                                        "Please add lots/serial number for existing scanned product."),
                                })
                            packages_line_with_package_type_and_current_product_id.package_qty += 1
                        else:
                            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                'title': _("Warning"),
                                'message': _(
                                    "Please select appropriate package type for existing scanned product."),
                            })
                    elif not packages_line_with_current_product_id:
                        if not product.packaging_ids:
                            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                'title': _("Warning"),
                                'message': _(
                                    "Please configure packaging with current scanned product"),
                            })
                        self.current_scanning_product_id = product.id
                        self.current_package_type_id = False
                        self.current_scanning_lot_id = False
                        vals.update({
                            'product_id': product.id

                        })
                else:
                    if not product.packaging_ids:
                        return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                            'title': _("Warning"),
                            'message': _(
                                "Please configure packaging with current scanned product"),
                        })
                    self.current_scanning_product_id = product.id
                    vals = {
                        'product_id': product.id
                    }
                if vals:
                    self.write({
                        'inner_package_line_ids': [(0, 0, vals)]
                    })

        else:
            package = self.env['stock.quant.package'].sudo().search([('name', '=', barcode)], limit=1)
            outer_package_line = self.outer_package_line_ids
            if package.contained_qty:
                quant_ids = package.quant_ids
                if len(quant_ids) > 1:
                    return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'title': _("Warning"),
                        'message': _(
                            "Please add proper package"),
                    })

                outer_package_line = outer_package_line.filtered(lambda x: x.product_id.id == quant_ids.product_id.id)
                if outer_package_line:
                    if package.id not in outer_package_line.product_package_ids.ids:
                        outer_package_line.write({
                            'product_package_ids': [(4, package.id)]
                        })
                else:

                    vals = {
                        'product_id': package.quant_ids.product_id.id,
                        'product_package_ids': [(4, package.id)]
                    }
                    self.write({
                        'outer_package_line_ids': [(0, 0, vals)]
                    })

    def action_generate_and_print_barcodes(self):
        """
        Author: Ishani Manvar
        Purpose: To generate a url which triggers a controller.
        """
        return {
            'name': 'Barcode',
            'type': 'ir.actions.act_url',
            'url': '/binary/package_barcodes?id={}&filename={}'.format(
                self.id, "{}_Package_Barcodes.pdf".format(len(self.setu_package_ids.ids))),
            'target': 'self',
        }

    @api.depends('outer_package_line_ids.package_count')
    def _compute_package_count(self):
        for rec in self:
            rec.package_count = sum(rec.outer_package_line_ids.mapped('package_count'))

    def do_package_weight(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("setu_product_packages.package_weight_wizard_action")
        action['context'] = {'default_package_id': self.id, 'package_lot_id': self.lot_id.id}
        return action

    def create_quant_package(self):
        return self.env['stock.quant.package'].create({
            'company_id': self.company_id.id,
            'package_type_id': self.packaging_id.package_type_id.id
        })

    def convert_product_and_create_packages(self):
        lot_id = self.lot_id
        if self.product_id.put_in_pack_product_id.id:
            qty = len(self.inner_package_line_ids) * self.packaging_id.qty
            mo_id = self.create_and_validate_package_mo(self.product_id, qty)
            mo_id = mo_id.with_context(avoid_reserved_qty_check=True, apply_package_domain=True)
            if self.product_id.tracking != 'none':
                exist_lot = self.env['stock.lot'].search(
                    [('product_id', '=', self.product_id.id), ('name', '=ilike', lot_id.name)], limit=1)
                if not exist_lot:
                    mo_id.action_generate_serial()
                    mo_id.lot_producing_id.name = lot_id.name
                else:
                    mo_id.lot_producing_id = exist_lot.id
            self.reserve_based_on_lot_and_mark_done(mo_id, self.lot_id)
            lot_id = mo_id.lot_producing_id
        try:
            self.create_internal_transfer_and_generate_package(lot_id)
        except Exception as e:
            raise UserError("Error {} comes at the time of creating Internal Transfer".format(e))
        self.setu_package_ids = self.inner_package_line_ids.mapped('quant_package_id')
        self.write({'package_state': 'done'})

    def create_and_validate_package_mo(self, product_id, qty):
        bom_id = product_id.bom_ids.filtered(lambda bom: bom.type == 'packaging')[:1]
        if not bom_id:
            raise UserError("Please create bill of material with Packaging Type")
        vals = {
            'product_id': product_id.id,
            'bom_id': bom_id.id,
            'product_qty': qty,
            'product_uom_id': bom_id.product_uom_id.id,
        }
        if hasattr(product_id, 'source_location_id') and product_id.source_location_id:
            vals.update({'location_src_id': product_id.source_location_id.id})
        if hasattr(product_id, 'destination_location_id') and product_id.destination_location_id:
            vals.update({'location_dest_id': product_id.destination_location_id.id})
        mo = self.env["mrp.production"].create(vals)
        mo.action_confirm()
        mo.write({'qty_producing': qty})
        return mo

    def reserve_based_on_lot_and_mark_done(self, mo_id, lot_ids):
        if self.product_tracking != 'none':
            mo_id.do_unreserve()
            self.update_move_qty_based_on_package_weight(mo_id.move_raw_ids)
            self.env['stock.picking'].do_unreserve_and_reserve_based_on_lot(mo_id.move_raw_ids, lot_ids)
        mo_id.move_raw_ids.picked = True
        action = mo_id.button_mark_done()
        if action and isinstance(action, dict) and action.get('res_model') == 'mrp.consumption.warning':
            consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
            consumption_warning.save().action_confirm()

    def update_move_qty_based_on_package_weight(self, move_ids):
        for move in move_ids:
            move.product_uom_qty = sum(self.inner_package_line_ids.mapped('weight'))

    def create_internal_transfer_and_generate_package(self, lot_ids):
        vals = self.prepare_internal_picking_vals()
        picking = self.env["stock.picking"].with_context(apply_package_domain=True).create(vals)
        picking.action_confirm()
        for line in self.inner_package_line_ids:
            line.quant_package_id.write({
                'total_weight': line.weight
            })
            move = self.env["stock.move"].create(self._prepare_stock_move_vals(picking))
            if lot_ids:
                picking.with_context(apply_package_domain=True).do_unreserve_and_reserve_based_on_lot(move, lot_ids)
            move.move_line_ids.write({'result_package_id': line.quant_package_id.id})
        picking.button_validate()

    def prepare_internal_picking_vals(self):
        picking_type = self.env["stock.picking.type"].search([('code', '=', 'internal'),
                                                              '|', (
                                                              'company_id', '=', self.source_location_id.company_id.id),
                                                              ('company_id', '=', False)], limit=1)
        if not picking_type:
            raise UserError("Please define Internal Location Type!")
        location_id = picking_type.default_location_src_id
        location_dest_id = picking_type.default_location_dest_id
        if self.product_id.put_in_pack and hasattr(self.product_id, 'destination_location_id'):
            location_id = self.product_id.destination_location_id or location_id
            location_dest_id = self.product_id.destination_location_id or location_dest_id
        return {
            'picking_type_id': picking_type.id,
            'user_id': False,
            'date': fields.datetime.today(),
            'origin': self.name,
            'location_dest_id': location_dest_id.id,
            'location_id': location_id.id,
            'company_id': self.company_id.id,
        }

    def _prepare_stock_move_vals(self, picking):
        self.ensure_one()
        return {
            'name': _('New Move:') + self.product_id.display_name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.packaging_id.qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'state': picking.state,
            'picking_type_id': picking.picking_type_id.id,
            'company_id': picking.company_id.id,
            'partner_id': picking.partner_id.id,
        }
