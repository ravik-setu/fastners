from odoo import fields, models, api, _
import pandas as pd
from datetime import datetime


class SetuGateEntryDetails(models.Model):
    _name = "setu.gate.entry.details"
    _description = "Setu Entry Gate Details"

    @api.model
    def dashboard_data_gate_entry(self, id, button):
        query = """
            SELECT type, COUNT(*)
            FROM setu_gate_entry_register
            WHERE date = CURRENT_DATE
            GROUP BY type;
        """
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        data_cards = {entry['type'] if entry['type'] else 'unknown': entry['count'] for entry in data}
        query_inward = """
            SELECT 
                name,
                date, 
                visitor_name, 
                visitor_vehicle_no, 
                visitor_company,
                type,
                id,
                state,
                reason,
                --un_visitor_name,
                --un_visitor_in_time,
                --un_visitor_out_time,
                in_time_visitor,
                out_time_visitor,
                visitor_contact,
                --un_visitor_vehicle_no,
                --un_visitor_contact,
                CASE 
                    WHEN state = 'in' THEN 'In'
                    WHEN state = 'out' THEN 'Out'
                    WHEN state = 'on_way' THEN 'On Way'
                    ELSE state 
                END AS state_label
            FROM 
                setu_gate_entry_register 
            WHERE 
                date = CURRENT_DATE;
        """

        self._cr.execute(query_inward)
        data_inward = self._cr.dictfetchall()
        if data_inward:
            data_inward = pd.DataFrame(data_inward)

            if 'date' in data_inward.columns:
                data_inward['date'] = pd.to_datetime(data_inward['date']).dt.strftime('%Y-%m-%d')

            datetime_fields = ['in_time_visitor', 'out_time_visitor']

            for field in datetime_fields:
                if field in data_inward.columns:
                    data_inward[field] = data_inward[field].apply(
                        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else None
                    )

            inward_records = (
                data_inward[data_inward['type'] == 'inward']
                [['date', 'visitor_name', 'visitor_vehicle_no', 'visitor_company', 'state','id','name']]
                .assign(state=lambda df: df['state'].replace({'on_way': 'On way','in':'In','out':'Out'}))
                .to_dict(orient="index")
            )

            outward_records = (
                data_inward[data_inward['type'] == 'outward']
                [['date', 'visitor_name', 'visitor_vehicle_no', 'visitor_company',
                  'reason','id','state','type']]
                .assign(state=lambda df: df['state'].replace({'on_way': 'On way', 'in': 'In', 'out': 'Out'}))
                .to_dict(orient="index")
            )
            visitor_records = (
                data_inward[data_inward['type'] == 'visitor']
                [['visitor_name', 'in_time_visitor', 'out_time_visitor', 'visitor_vehicle_no',
                  'visitor_contact','id','state','type']]
                .to_dict(orient="index")
            )
            if id:
                record = self.env['setu.gate.entry.register'].search([('id','=',id)])
                if record:
                    if button:
                        record.write({
                            'out_time_visitor':datetime.now(),
                            'state':'in',
                        })
                    else:
                        record.write({
                            'out_time_visitor': datetime.now(),
                            'state': 'out',
                        })
            dic = {
                'inward_count':data_cards.get('inward'),
                'inward_records':inward_records,
                'visitor_count':data_cards.get('visitor'),
                'visitor_records':visitor_records,
                'outward_records':outward_records,
                'outward_count':data_cards.get('outward'),
            }
            return dic
        else:
            return {}

