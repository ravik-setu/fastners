from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    inspection_sheet_id = fields.Many2one('setu.quality.check.sheet', compute='_get_inspection_sheet', store=True)
    no_inspect = fields.Boolean()
    quality_checks = fields.Many2many('setu.quality.check', compute="get_quality_checks_ids")

    def get_quality_checks_ids(self):
        for move_line in self:
            quality_check1 = move_line.env['setu.quality.check'].search(
                [('product_id', '=', move_line.product_id.id), ('picking_id', '=', move_line.picking_id.id)])
            move_line.quality_checks = [(6, 0, quality_check1.ids)]

    @api.depends('product_id', 'picking_id', 'lot_id')
    def _get_inspection_sheet(self):
        for rec in self:
            if rec.picking_id:
                quality_check = rec.env['setu.quality.check'].search(
                    [('product_id', '=', rec.product_id.id), ('picking_id', '=', rec.picking_id.id),
                     ('lot_id', '=', False), ('quality_state', '!=', 'cancel')])
                if quality_check:
                    for check in quality_check:
                        if rec.lot_id.id and not rec.no_inspect:
                            check.lot_id = rec.lot_id.id
                            rec.inspection_sheet_id = check.inspection_sheet_id.id
                            check.create_or_not = True

                    for move_line in rec.picking_id.move_line_ids:
                        if move_line.lot_id:
                            # Used Search Function for Qulity Check[lot_id not storing in table is shows null]
                            new_quality_check = rec.env['setu.quality.check'].search(
                                [('product_id', '=', rec.product_id.id), ('picking_id', '=', rec.picking_id.id),
                                 ('lot_id', '=', move_line.lot_id.id), ('quality_state', '!=', 'cancel')])
                            if not new_quality_check:
                                for check in quality_check:
                                    if check.point_id:
                                        # Used Search Function for Qulity Check[lot_id not storing in table is shows null]
                                        new_quality_check = rec.env['setu.quality.check'].search(
                                            [('product_id', '=', rec.product_id.id),
                                             ('picking_id', '=', rec.picking_id.id),
                                             ('point_id', '=', check.point_id.id), ('quality_state', '!=', 'cancel')])
                                        if not new_quality_check:
                                            vals = {
                                                'point_id': check.point_id.id,
                                                'product_id': move_line.product_id.id,
                                                'picking_id': move_line.picking_id.id,
                                                'lot_id': move_line.lot_id.id,
                                                'test_type_id': check.test_type_id.id,
                                                'team_id': check.team_id.id,
                                                'company_id': move_line.company_id.id
                                            }
                                            check = rec.env['setu.quality.check'].create(vals)
                                            rec.inspection_sheet_id = check.inspection_sheet_id.id

                else:
                    quality_check = rec.env['setu.quality.check'].search(
                        [('product_id', '=', rec.product_id.id), ('picking_id', '=', rec.picking_id.id),
                         ('create_or_not', '=', True), ('quality_state', '!=', 'cancel')])
                    if quality_check and rec.location_dest_id.reject_location == False:
                        # Used Search Function for Qulity Check[lot_id not storing in table is shows null]
                        new_quality_check = rec.env['setu.quality.check'].search(
                            [('product_id', '=', rec.product_id.id), ('picking_id', '=', rec.picking_id.id),
                             ('lot_id', '=', rec.lot_id.id), ('quality_state', '!=', 'cancel')])
                        if not new_quality_check:
                            for check in quality_check:
                                if check.point_id:
                                    # Used Search Function for Qulity Check[lot_id not storing in table is shows null]
                                    new_quality_check = rec.env['setu.quality.check'].search(
                                        [('product_id', '=', rec.product_id.id), ('picking_id', '=', rec.picking_id.id),
                                         ('lot_id', '=', rec.lot_id.id), ('point_id', '=', check.point_id.id),
                                         ('quality_state', '!=', 'cancel')])
                                    if not new_quality_check:
                                        vals = {
                                            'point_id': check.point_id.id,
                                            'product_id': rec.product_id.id,
                                            'picking_id': rec.picking_id.id,
                                            'lot_id': rec.lot_id.id,
                                            'test_type_id': check.test_type_id.id,
                                            'team_id': check.team_id.id,
                                            'company_id': rec.company_id.id
                                        }
                                        check = rec.env['setu.quality.check'].create(vals)
                                        rec.inspection_sheet_id = check.inspection_sheet_id.id

            elif rec.move_id.production_id:
                quality_check = rec.env['setu.quality.check'].search(
                    [('product_id', '=', rec.product_id.id), ('production_id', '=', rec.move_id.production_id.id),
                     ('lot_id', '=', False), ('quality_state', '!=', 'cancel')])
                if quality_check:
                    for check in quality_check:
                        if rec.lot_id.id and not rec.no_inspect:
                            check.lot_id = rec.lot_id.id
                            rec.inspection_sheet_id = check.inspection_sheet_id.id
                            check.create_or_not = True
                            # check.copy({'lot_id':rec.lot_id.id})
                else:
                    quality_check = rec.env['setu.quality.check'].search(
                        [('product_id', '=', rec.product_id.id), ('production_id', '=', rec.move_id.production_id.id),
                         ('create_or_not', '=', True), ('quality_state', '!=', 'cancel')])
                    if quality_check:
                        for check in quality_check:
                            vals = {
                                'product_id': rec.product_id.id,
                                'picking_id': rec.picking_id.id,
                                'lot_id': rec.lot_id.id,
                                'test_type_id': check.test_type_id.id,
                                'team_id': check.team_id.id,
                                'company_id': rec.company_id.id
                            }
                            check = rec.env['setu.quality.check'].create(vals)
                            rec.inspection_sheet_id = check.inspection_sheet_id.id
