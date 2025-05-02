from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuQcParameters(models.Model):
    _name = 'setu.qc.parameters'
    _description = "Quality Checks Parameters"
    _inherit = 'mail.thread'
    _rec_name = 'product_id'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    parameter_line_ids = fields.One2many(comodel_name="setu.qc.parameter.lines", inverse_name="qc_parameter_id",
                                         string="Parameters")
    worksheet_templ_id = fields.Many2one(comodel_name='ir.model', string='Worksheet')
    active = fields.Boolean(string="Active", default=True)

    @api.constrains('product_id')
    def check_unique(self):
        duplicate_records = self.search([('product_id', '=', self.product_id.id), ('active', '=', True)])
        if len(duplicate_records) > 1:
            raise ValidationError(
                _("Only one QC Parameter is allowed per product. Archive the existing one to create a new."))

    def create_worksheet_field(self, fields):
        field_obj = self.env["ir.model.fields"]
        for field in fields:
            fields[field].update({'name': field})
            if qc_field := field_obj.search([('name', '=', field), ('model_id', '=', fields[field]['model_id'])]):
                if 'selection_ids' in fields[field]:
                    fields[field].pop('selection_ids')
                qc_field.write(fields[field])
            else:
                self.env["ir.model.fields"].create(
                    [
                        fields[field]
                    ]
                )
        return True

    def get_dynamic_form_view(self):
        arch = """<form create="false" js_class="worksheet_validation">
                                           <sheet>
                                               <group>
                                                   <!-- General Information Section -->
                                                   <group string="INFO">
                                                       <field name="x_partner_id"/>
                                                       <field name="x_certificate_no"/>
                                                       <field name="x_certificate_date"/>
                                                       <field name="x_sampling_date"/>
                                                       <field name="x_company_id" widget="many2one"/>
                                                   </group>

                                                   <!-- Product Details Section -->
                                                   <group string="Product Info">
                                                       <field name="x_product_id" widget="many2one"/>
                                                       <field name="x_lot_id" widget="many2one"/>
                                                       <field name="x_quantity"/>
                                                       <field name="x_no_of_bags"/>
                                                       <field name="x_packing_id" widget="many2one" />
                                                   </group>
                                               </group>
                                       """
        field_count = 0
        field_group1 = ""
        field_group2 = ""

        for parameter in self.parameter_line_ids.sorted('sequence'):
            base_property = parameter.base_property
            field_name = f'x_{parameter.parameter_name.replace(" ", "_").lower()}'

            parameter.parameter_tech_name = field_name
            field_count += 1
            is_required = True if base_property == 'required' else False
            is_invisible = True if base_property == 'invisible' else False
            if field_count % 2 == 0:
                field_group2 += f"""<field name="{field_name}" required="{is_required}" invisible="{is_invisible}"/>"""
            else:
                field_group1 += f"""<field name="{field_name}" required="{is_required}" invisible="{is_invisible}"/>"""

        arch += f"""
                        <!-- Dynamic Parameters -->
                        <group string="Test Parameters">
                            <group> 
                                {field_group1}
                            </group>
                            <group> 
                                {field_group2}
                            </group>
                        </group>
                    </sheet>
                </form>"""
        return arch

    def generate_worksheet(self):
        # Create the worksheet template
        model_seq = self.env['ir.sequence'].next_by_code('setu.worksheet.template')
        template_id = self.env['ir.model'].create({'name': self.product_id.display_name,
                                                'model': f'x_setu.worksheet.template_{model_seq}',
                                                'state': 'manual'
                                                })
        self.env['ir.model.access'].create({'name': f'x_setu.worksheet.template_{model_seq}',
                                            'model_id': template_id.id,
                                            'group_id': self.env.ref('base.group_user').id,
                                            'perm_read': True,
                                            'perm_write': True,
                                            'perm_create': True,
                                            'perm_unlink': False})
        self.write({'worksheet_templ_id': template_id.id})

        fields = {
            "x_certificate_no": {"ttype": "char", "field_description": "Certificate No.",
                                 "model_id": template_id.id},
            "x_certificate_date": {"ttype": "date", "field_description": "Certificate Date",
                                   "model_id": template_id.id},
            "x_sampling_date": {"ttype": "date", "field_description": "Sampling Date",
                                "model_id": template_id.id},
            "x_partner_id": {"ttype": "many2one", "relation": 'res.partner', "field_description": "vendor",
                             "model_id": template_id.id},
            "x_product_id": {"ttype": "many2one", "relation": 'product.product', "field_description": "Product",
                             "model_id": template_id.id},
            "x_company_id": {"ttype": "many2one", "relation": 'res.company', "field_description": "Company",
                             "model_id": template_id.id},
            "x_quantity": {"ttype": "float", "field_description": "Quantity", "model_id": template_id.id},
            "x_no_of_bags": {"ttype": "float", "field_description": "No. of Bags", "model_id": template_id.id},
            "x_packing_id": {"ttype": "many2one", "relation": 'product.packaging', "field_description": "Packing",
                             "model_id": template_id.id},
            "x_lot_id": {"ttype": "many2one", "relation": 'stock.lot', "field_description": "Lot no.",
                         "model_id": template_id.id},
        }
        for parameter in self.parameter_line_ids:
            field_name = f'x_{parameter.parameter_name.replace(" ", "_").lower()}'
            fields[field_name] = {
                "ttype": parameter.parameter_dt,
                "field_description": parameter.parameter_name,
                "model_id": template_id.id,
                "help": parameter.description
            }
        self.create_worksheet_field(fields)

        arch = self.get_dynamic_form_view()
        vals = {
            "name": {self.product_id.name},
            "model": template_id.model,
            "priority": 10,
            "type": "form",
            "arch": arch
        }
        self.env["ir.ui.view"].create(vals)

        return True


    def update_worksheet(self):
        if not self.worksheet_templ_id:
            return True
        # Get the view for the model
        view = self.env["ir.ui.view"].search([
            ("model", "=", self.worksheet_templ_id.model),
            ("type", "=", "form"),
        ], limit=1)

        fields={}
        for parameter in self.parameter_line_ids:
            field_name = f'x_{parameter.parameter_name.replace(" ", "_").lower()}'
            fields[field_name] = {
                "ttype": parameter.parameter_dt,
                "field_description": parameter.parameter_name,
                "model_id": self.worksheet_templ_id.id,
                "help": parameter.description
            }
        self.create_worksheet_field(fields)

        arch = self.get_dynamic_form_view()
        vals = {
            "name": {self.product_id.name},
            "model": self.worksheet_templ_id.model,
            "priority": 10,
            "type": "form",
            "arch": arch
        }
        if view:
            view.write(vals)
        else:
            view.create(vals)
        return True



