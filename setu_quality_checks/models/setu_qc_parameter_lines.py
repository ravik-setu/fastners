from odoo import models, fields


class SetuQcParametersLines(models.Model):
    _name = "setu.qc.parameter.lines"
    _description = "Quality Checks Parameters Lines for worksheet"

    qc_parameter_id = fields.Many2one(comodel_name="setu.qc.parameters",string="Quality Checks")
    parameter_name = fields.Char(string="Parameter")
    parameter_tech_name = fields.Char(string="Technical Name")
    parameter_dt = fields.Selection(
        selection=[
            ('char', "Char"),
            ('integer', "Integer"),
            ('float', "Float"),
            ('boolean', "Boolean"),
        ],string="Data Type")
    description = fields.Char(string="Description")
    base_property = fields.Selection(selection=[('required',"Required"),('invisible',"Invisible")])
    sequence = fields.Integer(string="Sequence")