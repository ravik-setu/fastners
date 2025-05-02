# -*- coding: utf-8 -*-
{
    # App information
    'name': 'Currency Forward Booking / Currency Hedging',
    'version': '1.0',
    'license': 'LGPL-3',

    'summary': """
    	Setu Currency Forward Booking Management,
    	Currency Management, Foreign Exchange, Currency Rate, Cash Management, Cash Exchange, Exchange Rate, International Transactions,
	Profit and Loss, Financial Tracking, Bank Currency Rate, Payment Tracking, Financial Oversight, Currency Forward Booking,
	Currency Management System, Accounting Management, Financial Insights, Financial Reporting, Transaction Management,
	Cost of Transactions, Payment Balances, Cash Flow Management, Currency Deals, Exchange Rate Management, Forward Booking Management,
	Currency Hedging, Position Hedging, Position Hashing, Currency Hashing, Forward contracts, Currency Forward contracts,
	Currency swaps, Currency Hedging, Position Hedging,
    	""",

    'description': """
    	Our Currency Forward Booking Application transforms how you handle international transactions within the Odoo ERP system. This specialized 
    	tool offers a structured approach to managing exchange rate fluctuations and complex financial tracking. Set future exchange rates through 
    	negotiations with banks, ensuring you lock in favorable rates and mitigate the impact of currency rate variations. Simplify your 
    	international transactions with clear tracking of payments and remaining balances, all in one place. Gain real-time insights into profit and 
    	loss to make informed financial decisions and access detailed information on deal cancellations and closures. Organize all related payments 
    	and bank fees efficiently. Ideal for businesses managing foreign exchange and cash management, this application enhances your currency 
    	management and financial oversight capabilities. Optimize your global operations and safeguard against unforeseen losses with our 
    	comprehensive currency forward booking solution, available in the Odoo app store.
    	""",

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',

    'images': ['static/description/banner.gif'],

    # Dependencies
    'depends': ['sale_management', 'stock'],

    # Views
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'wizard/setu_payment_schedule_booking_wizard_view.xml',
        'data/payment_schedule_data.xml',
        'views/setu_forward_booking_view.xml',
        'views/setu_bank_charges.xml',
        'views/setu_payment_schedule_view.xml',
        'views/sale_order_view.xml',
        'views/account_move_view.xml',
        'wizard/account_payment_register_view.xml'
    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
}
