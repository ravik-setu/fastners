from odoo import fields, models, api


class QualityPoint(models.Model):
    _inherit = "setu.quality.point"

    inspection_plan_id = fields.Many2one('setu.quality.check.plan', ondelete='cascade')
    team_id = fields.Many2one(
        'setu.quality.alert.team', 'Team', check_company=True,
        default=False, required=False,
        compute='_compute_details', store=True, readonly=False )
    product_ids = fields.Many2many(
        'product.product', string='Products',
        compute='_compute_details', store=True, readonly=False)
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', required=False, check_company=True,
        domain="[('type', 'in', ['consu', 'product']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        compute='_compute_details', store=True, readonly=False)
    picking_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types', required=True, check_company=True,
        compute='_compute_details', store=True, readonly=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=False, index=True, default=False,
        compute='_compute_details', store=True, readonly=False)
    code = fields.Char(compute="_compute_details", store=True)
    is_readonly = fields.Boolean(default=False,copy=False,compute="_compute_readonly")

    test_method_id = fields.Many2one('setu.quality.test.method')
    characteristic = fields.Many2one('setu.quality.characteristic')

    @api.onchange('product_ids')
    def _onchange_product_id(self):
        for point in self:
            if point.product_ids:
                point.product_category_ids = [(6,0,point.product_ids.categ_id.mapped('id'))]
            else:
                point.product_category_ids = False

    def add_items(self):
        value = self.env['setu.quality.point'].search([('product_tmpl_id', '=', self.inspection_plan_id.product_tmpl_id.id), (
            'picking_type_ids', 'in', self.inspection_plan_id.picking_type_id.id), ('team_id', '=', self.inspection_plan_id.team_id.id)])
        return {
            'name': 'Quality Points',
            'view_mode': 'tree',
            'res_model': 'setu.quality.point',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('product_tmpl_id', '=', self.inspection_plan_id.product_tmpl_id.id), ('inspection_plan_id', '==', False), ('picking_type_ids', '=', self.inspection_plan_id.picking_type_id.id), ('team_id', '=', self.inspection_plan_id.team_id.id)],

        }

    def select_button(self):
        inspect = self.env['setu.quality.check.plan'].browse(
            self._context.get('plan_id'))
        if inspect:
            for rec in self:
                rec.write({'inspection_plan_id': inspect.id})

    @api.depends('product_ids', 'product_tmpl_id', 'product_category_ids')
    def _compute_readonly(self):
        for rec in self:
            if rec.inspection_plan_id and rec.product_ids and rec.product_tmpl_id and rec.product_category_ids:
                rec.is_readonly = True
            else:
                rec.is_readonly = False

    @api.depends('inspection_plan_id', 'inspection_plan_id.product_ids', 'inspection_plan_id.picking_type_ids',
                 'inspection_plan_id.team_id')
    def _compute_details(self):
        for rec in self:
            if rec.inspection_plan_id:
                rec.product_ids = [(6, 0, rec.inspection_plan_id.product_ids.ids)]
                rec.picking_type_ids = [(6, 0, rec.inspection_plan_id.picking_type_ids.ids)]
                rec.product_category_ids = [(6, 0, rec.inspection_plan_id.product_category_ids.ids)]
                rec.team_id = rec.inspection_plan_id.team_id.id
                rec.company_id = rec.inspection_plan_id.company_id.id
                rec.code = rec.picking_type_ids.code
            else:
                rec.product_tmpl_id = rec.picking_type_ids = rec.team_id = rec.code = False

    @api.onchange('characteristic')
    def _set_title(self):
        self.title = self.characteristic.description
