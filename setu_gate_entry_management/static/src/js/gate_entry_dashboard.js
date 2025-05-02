/** @odoo-module **/
import * as BarcodeScanner from '@web/webclient/barcode/barcode_scanner';
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
//import { bus } from 'web.core';
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";

//var core = require('web.core');
//var QWeb = core.qweb;
//var rpc = require('web.rpc');


export class SetuGateEntryDetailsDashboard extends Component {
    setup() {

        this.actionService = useService("action");
        this.orm = useService("orm");
        this.context = session.user_context;
        this.state = useState({});
        this.data = null;
        this.id = null;
        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();
        onWillStart(async () => {
            this.data = await this.orm.call("setu.gate.entry.details", "dashboard_data_gate_entry", [this.id,[]]);
            console.log(this.data)
        });

        onMounted(() => {

            this.initializeDashboard();
        });
    }

    async initializeDashboard() {
        debugger
        document.querySelector(".inward_value").textContent = this.data.inward_count || 0;
        document.querySelector(".visitor_value").textContent = this.data.visitor_count || 0;
        document.querySelector(".outward_value").textContent = this.data.outward_count || 0;
        document.querySelector(".button_back").style.display = "none";
        document.querySelector(".barcode_screen_inward").style.display = "none";

        document.querySelector(".inward").addEventListener('click', async (event) => {
            document.querySelector(".main_div").style.display = "none"
            document.querySelector(".button_back").style.display = "block";
            document.querySelector(".barcode_screen_inward").style.display = "block";
        });

        document.querySelector(".button_back").addEventListener('click', async (event) => {
            document.querySelector(".main_div").style.display = "block"
            document.querySelector(".button_back").style.display = "none";
            document.querySelector(".barcode_screen_inward").style.display = "none";
        });
        document.querySelectorAll(".in_button").forEach(button => {
            button.addEventListener('click', async (event) => {
                event.stopPropagation();
                debugger;

                let row = event.target.closest("tr");
                let contact = row.cells[4].innerText.trim();


                let id = row.cells[5].innerText.trim();

                let now = new Date();
                let formattedTime = now.getFullYear() + "-" +
                                    String(now.getMonth() + 1).padStart(2, '0') + "-" +
                                    String(now.getDate()).padStart(2, '0') + " " +
                                    String(now.getHours()).padStart(2, '0') + ":" +
                                    String(now.getMinutes()).padStart(2, '0') + ":" +
                                    String(now.getSeconds()).padStart(2, '0');

                row.cells[2].innerText = formattedTime;
                event.target.style.display = "none";
                let button = "in_button"
                    await this.orm.call("setu.gate.entry.details", "dashboard_data_gate_entry", [id,button ]);
            });
        });

        document.querySelectorAll(".out_button button").forEach(button => {
            button.addEventListener('click', async (event) => {
                event.stopPropagation();
                ;

                let row = event.target.closest("tr");
                let contact = row.cells[4].innerText.trim();


                let id = row.cells[5].innerText.trim();

                let now = new Date();
                let formattedTime = now.getFullYear() + "-" +
                                    String(now.getMonth() + 1).padStart(2, '0') + "-" +
                                    String(now.getDate()).padStart(2, '0') + " " +
                                    String(now.getHours()).padStart(2, '0') + ":" +
                                    String(now.getMinutes()).padStart(2, '0') + ":" +
                                    String(now.getSeconds()).padStart(2, '0');

                row.cells[2].innerText = formattedTime;
                event.target.style.display = "none";

                await this.orm.call("setu.gate.entry.details", "dashboard_data_gate_entry", [id,[]]);
            });
        });




        document.querySelector(".visitor").addEventListener('click', async (event) => {

            this.context = { ...session.user_context, type: 'visitor' };
            this.actionService.doAction({
                    name: 'Visitor Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    context:{
                        'default_type': 'visitor'
                    },
            });
        });
        document.querySelector(".outward").addEventListener('click', async (event) => {
        debugger
            this.actionService.doAction({
                    name: 'Outward Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    context:{
                        'default_type': 'outward'
                    }
            });
            this.context = { ...session.user_context, type: 'outward' };
        });
        document.querySelectorAll(".selected_row").forEach(row => {
            row.closest("td").addEventListener('click', async (event) => {
                let rowElement = event.target.closest("tr");
                let id = rowElement.querySelector(".id").innerText.trim();
                let id_new = parseInt(id);


                this.actionService.doAction({
                    name: 'Visitor Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    res_id: id_new,
                    domain: [['id', '=', id_new]],
                });
            });
        });
        document.querySelectorAll(".selected_row_outward").forEach(row => {

            row.closest("td").addEventListener('click', async (event) => {

                let rowElement = event.target.closest("tr");
                let id = rowElement.querySelector(".id").innerText.trim();
                let id_new = parseInt(id);
                this.context = { ...session.user_context, type: 'outward' };
                this.actionService.doAction({
                    name: 'Outward Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    res_id: id_new,
                });
            });
        });
        document.querySelectorAll(".selected_row_inward").forEach(row => {
            row.closest("td").addEventListener('click', async (event) => {
                let rowElement = event.target.closest("tr");
                let id = rowElement.querySelector(".id").innerText.trim();
                let id_new = parseInt(id);


                this.actionService.doAction({
                    name: 'Visitor Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    res_id: id_new,
                    domain: [['id', '=', id_new]],
                });
            });
        });
    }
    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode();
        console.log(barcode)
        if (barcode) {
            this._processBarcode(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.env.services.notification.add(
                this.env._t("Please, Scan again !"),
                {type: 'warning'}
            );
        }
    }
    openView(){

        var barcode = document.querySelector(".manual_barcode").value
        this._processBarcode(barcode);
    }
    async _processBarcode(barcode){

        const records = await this.orm.searchRead(
            "setu.gate.entry.register",
            [
                ['visitor_vehicle_no', 'ilike', barcode],
                ['state', '=', 'on_way']
            ],
            ['id']
        );
        console.log(records)
        const ids = records.map(record => record.id);
        console.log(ids)
        if (records.length > 1) {
            this.actionService.doAction({
                    name: 'Inward Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'tree,form',
                     views: [[false, 'tree'], [false, 'form']],
                    domain: [
                        ['id', 'in', ids]
                    ],
                    context:{
                        'editable':true,

                    }
        });
        } else if (records.length === 1) {
            this.actionService.doAction({
                    name: 'Inward Entries',
                    type: 'ir.actions.act_window',
                    res_model: 'setu.gate.entry.register',
                    view_type: 'form',
                    views: [[false, 'form']],
                    domain: [
                        ['id', 'in', ids]
                    ],
                    res_id: records[0].id,
        });
        }

    }

}

SetuGateEntryDetailsDashboard.template = "SetuGateEntryDetailsDashboard";
registry.category("actions").add("setu_gate_entry_management", SetuGateEntryDetailsDashboard);
