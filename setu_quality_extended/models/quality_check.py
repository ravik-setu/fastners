from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class QualityCheck(models.Model):
    _inherit = "setu.quality.check"

    inspection_sheet_id = fields.Many2one(
        'setu.quality.check.sheet', compute='_get_inspection_sheet', inverse="inverse_quality_check", store=True)
    create_or_not = fields.Boolean()
    picking_type_ids = fields.Many2many('stock.picking.type', string='Operation Types')

    test_product_id = fields.Many2one('product.product', related='inspection_sheet_id.product_id')
    production_id = fields.Many2one("mrp.production", string="Production Order")

    def inverse_quality_check(self):
        for rec in self:
            rec.point_id = rec.point_id
            rec.team_id = rec.team_id
            rec.title = rec.title
            rec.test_type = rec.test_type
            rec.test_type_id = rec.test_type_id
            rec.test_method_id = rec.test_method_id
            rec.measure = rec.measure
            rec.norm = rec.norm
            rec.norm_unit = rec.norm_unit
            rec.tolerance_min = rec.tolerance_min
            rec.tolerance_max = rec.tolerance_max
            rec.quality_state = rec.quality_state
            rec.inspection_sheet_id = rec.inspection_sheet_id

    def do_alert(self):
        self.ensure_one()
        alert = self.env['setu.quality.alert'].create({
            'check_id': self.id,
            'product_id': self.product_id.id,
            'product_tmpl_id': self.product_id.product_tmpl_id.id,
            'lot_id': self.lot_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'company_id': self.company_id.id,
            'picking_id': self.picking_id.id,
            'partner_id': self.inspection_sheet_id.partner_id.id,
            'source': self.inspection_sheet_id.source

        })
        return {
            'name': _('Quality Alert'),
            'type': 'ir.actions.act_window',
            'res_model': 'setu.quality.alert',
            'views': [(self.env.ref('setu_quality_control.setu_quality_alert_view_form').id, 'form')],
            'res_id': alert.id,
            'context': {'default_check_id': self.id},
        }

    @api.depends('product_id', 'picking_id', 'lot_id', 'picking_id.state')
    def _get_inspection_sheet(self):
        for rec in self:
            if (rec.production_id or rec.picking_id.state in ['assigned', 'done', 'cancel']) and (
                    rec.product_id.tracking != 'lot' or rec.lot_id):
                search_params = [('product_id', '=', rec.product_id.id),
                                 ('team_id', '=', rec.team_id.id,),
                                 ('company_id', '=', rec.company_id.id),
                                 ('state', '!=', 'cancel')]
                if rec.picking_id:
                    search_params.append(('picking_id', '=', rec.picking_id.id))
                if rec.lot_id:
                    search_params.append(('lot_id', '=', rec.lot_id.id))
                if rec.production_id:
                    search_params.append(('production_id', '=', rec.production_id.id))
                sheet = self.env['setu.quality.check.sheet'].search(search_params, limit=1).id
                inspection_sheet = self.env['setu.quality.check.sheet'].search(search_params, limit=1)

                value = 0
                if rec.picking_id.move_line_ids:
                    if rec.lot_id:
                        value = sum(rec.picking_id.move_line_ids.filtered(
                            lambda line: line.product_id == rec.product_id and line.lot_id == rec.lot_id).mapped(
                            'quantity'))
                    else:
                        value = sum(rec.picking_id.move_line_ids.filtered(
                            lambda line: line.product_id == rec.product_id).mapped('quantity'))
                if sheet:
                    if value > 0:
                        inspection_sheet.quantity_recieved = value
                if not sheet:
                    create_params = {'product_id': rec.product_id.id,
                                     'team_id': rec.team_id.id,
                                     'company_id': rec.company_id.id}

                    if rec.picking_id.move_line_ids:
                        value = sum(rec.picking_id.move_line_ids.filtered(
                            lambda line: line.product_id == rec.product_id and line.lot_id == rec.lot_id).mapped(
                            'quantity'))
                        if value > 0:
                            create_params.update({'quantity_recieved': value})

                    if rec.picking_id:
                        create_params.update({'picking_id': rec.picking_id.id})

                    if rec.lot_id:
                        create_params.update({'lot_id': rec.lot_id.id})
                    if rec.production_id:
                        create_params.update({'production_id': rec.production_id.id})
                        value = rec.production_id.qty_producing
                        create_params.update({'quantity_recieved': value})

                    if create_params.get('quantity_recieved'):
                        sheet = self.env['setu.quality.check.sheet'].create(create_params).id
                rec.inspection_sheet_id = sheet
            else:
                rec.inspection_sheet_id = False

    norm = fields.Float(related="point_id.norm")
    tolerance_min = fields.Float(related="point_id.tolerance_min")
    tolerance_max = fields.Float(related="point_id.tolerance_max")
    norm_unit = fields.Char(related="point_id.norm_unit")
    test_method_id = fields.Many2one(
        'setu.quality.test.method', related="point_id.test_method_id")

    quality_state = fields.Selection([
        ('none', 'To do'),
        ('pass', 'Passed'),
        ('fail', 'Failed'),
        ('cancel', 'Cancel')], string='Status', tracking=True,
        default='none', copy=False, store=True, compute='_set_state')

    confirm_measurement = fields.Boolean()

    @api.depends('test_type', 'measure', 'confirm_measurement')
    def _set_state(self):
        for rec in self:
            if rec.test_type == 'measure' and rec.confirm_measurement:
                # this condition for the negative values
                if not rec.tolerance_min >= 0.0 and not rec.tolerance_max > 0.0:
                    if rec.measure <= rec.tolerance_min and rec.measure >= rec.tolerance_max:
                        rec.quality_state = 'pass'
                    else:
                        rec.quality_state = 'fail'
                elif rec.measure >= rec.tolerance_min and rec.measure <= rec.tolerance_max:
                    rec.quality_state = 'pass'
                else:
                    rec.quality_state = 'fail'
            else:
                rec.quality_state = 'none'

    title = fields.Char(related="point_id.title")

    def confirm_measure_btn(self):
        if self.test_type == 'measure':
            self.confirm_measurement = True
        else:
            self.quality_state = 'pass'

    def fail_btn(self):
        self.quality_state = 'fail'

    def do_measure(self):
        if self.measure <= 0:
            raise UserError("Please fill data in Measure")
        return super(QualityCheck, self).do_measure()