from odoo import fields, models, api
from odoo.tools.misc import xlsxwriter
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class AccountReportWizard(models.TransientModel):
    _name = 'account.report.wizard'
    _description = 'Account report wizard'

    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 index=True, required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    datas = fields.Binary(string="Datas")

    def prepare_cashflow_vals(self):
        self._cr.execute("""select to_char(ap.create_date,'Mon') as Month, extract(year from ap.create_date) as year,
	        sum(case WHEN ap.payment_type = 'inbound' THEN ap.amount ELSE 0 END)as in_payment,
	        sum(case WHEN ap.payment_type = 'outbound' THEN ap.amount ELSE 0 END)as out_payment,
	        sum(case WHEN ap.payment_type = 'inbound' THEN ap.amount ELSE 0 END) - 
	        sum(case WHEN ap.payment_type = 'outbound' THEN ap.amount ELSE 0 END) as balance from account_payment ap
            join account_move am on am.id=ap.move_id
            join account_journal aj on aj.id = am.journal_id
            where create_date >= {} and create_date <= {}
            group by 1,2""".format(self.start_date, self.end_date))
        data = self._cr.fetchall()
        return data

    def download_cashflow_report(self):
        try:
            self.prepare_cashflow_vals()
        except Exception as e:
            _logger.info("===== ERROR COMES AT CASH FLOW REPORT DOWNLOAD : {}".format(e))
        file_pointer = BytesIO()
        workbook = xlsxwriter.Workbook(file_pointer)
        worksheet = workbook.add_worksheet('Cashflow Report')
        company_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 5, 'font_size': 11, })
        company_address_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 2, 'font_size': 9})
        report_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 5, 'font_size': 9})
        date_heading_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 3, 'font_size': 9})
        report_hearder_format = workbook.add_format(
            {'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': 4, 'font_size': 9})
        date_heading = "DATE - {} TO {}".format(self.start_date.strftime("%d-%m-%Y"),
                                                self.end_date.strftime("%d-%m-%Y"))
        worksheet.merge_range("A1:D2", self.company_id.name, company_heading_format)
        worksheet.merge_range("A3:D3", self.company_id.street, company_address_format)
        worksheet.merge_range("A4:D4",
                              "{}, {} - ({}), {}, {}".format(self.company_id.street2, self.company_id.city,
                                                             self.company_id.zip, self.company_id.state_id.name,
                                                             self.company_id.country_id.name),
                              company_address_format)
        worksheet.merge_range("A5:D5", "Cash Flow Report", report_heading_format)
        worksheet.merge_range("A6:D6", date_heading, date_heading_format)
        worksheet.merge_range("A7:A8", "Months", report_hearder_format)
        worksheet.merge_range("B7:C7", "Cash Movement", report_hearder_format)
        worksheet.write("B8", "InFlow", report_hearder_format)
        worksheet.write("C8", "Out Flow", report_hearder_format)
        worksheet.merge_range("D7:D8", "Net Flow", report_hearder_format)
        workbook.close()

        file_name = "{}to{}_cash_flow_report.xlsx".format(self.start_date.strftime("%d-%m-%Y"),
                                                          self.end_date.strftime("%d-%m-%Y"))
        file_pointer.seek(0)
        file_data = base64.encodebytes(file_pointer.read())
        self.write({'datas': file_data})
        file_pointer.close()
        return {
            'name': 'Cash Flow Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_xlsx_document?model=account.report.wizard&field=datas&id={}&filename={}'.format(
                self.id, file_name),
            'target': 'self',
        }

