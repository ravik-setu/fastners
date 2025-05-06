from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

# Inspection Plan
class SetuQualityCheckPlan(models.Model):
    _name = "setu.quality.check.plan"
    _inherit = ['mail.thread']
    _description = "Setu Quality Inspection Plan"

    name = fields.Char(tracking=True)
    team_id = fields.Many2one(
        'setu.quality.alert.team', 'Team', check_company=True, tracking=True)
    product_id = fields.Many2one(
        'product.product', domain="[('product_tmpl_id', '=', product_tmpl_id)]", tracking=True)
    product_tmpl_id = fields.Many2one(
        'product.template', check_company=True,
        domain="[('type', 'in', ['consu', 'product']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', "Operation Type", check_company=True, tracking=True)

    quality_point_ids = fields.One2many(
        'setu.quality.point', 'inspection_plan_id', check_company=True)

    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company, tracking=True)
    _sql_constraints = [('product_uniq', 'unique(picking_type_id, product_tmpl_id, product_id)',
                         'Inspection Plan for this Operation type and Product already exist.')]
    product_category_ids = fields.Many2many(
        'product.category', string="Product Categories")
    is_workorder_step = fields.Boolean(defualt=False)
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)
    picking_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types', required=True, check_company=True)
    product_ids = fields.Many2many(
        'product.product', string='Products',
        domain="[('type', 'in', ('product', 'consu')), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Quality Point will apply to every selected Products.")


    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        for plan in self:
            if plan.product_tmpl_id:
                plan.product_id = plan.product_tmpl_id.product_variant_id.id
            else:
                plan.product_category_ids = False


    def add_items(self):
        value = self.env['setu.quality.point'].search([('product_ids', '=', self.product_tmpl_id.product_variant_id.id), (
            'picking_type_ids', 'in', self.picking_type_ids.ids), ('team_id', '=', self.team_id.id), ('inspection_plan_id', '=', False)])
        return {
            'name': 'Quality Points',
            'view_mode': 'tree',
            'res_model': 'setu.quality.point',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'plan_id': self.id},
            'domain': [('product_ids', '=', self.product_tmpl_id.product_variant_id.id), ('picking_type_ids', 'in', self.picking_type_ids.ids), ('team_id', '=', self.team_id.id), ('inspection_plan_id', '=', False)],

        }

    @api.onchange('picking_type_id')
    def picking_type_ids_onchange(self):
        for rec in self:
            if rec.picking_type_id.code == 'mrp_operation':
                rec.is_workorder_step = True
            else:
                rec.is_workorder_step = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SetuQualityCheckPlan, self).create(vals_list)
        for res in records:
            sequence = res.picking_type_ids.sequence_for_inspection_plan
            if not sequence:
                raise UserError(
                    _("Please Enter The sequence for this operation Type"))
            res.name = sequence[0].next_by_id()
            res.quality_point_ids._compute_details()
        return records

    @api.constrains('start_date', 'end_date')
    def _check_quantities(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(
                    _("""End Date Can not be less than Start Date"""))