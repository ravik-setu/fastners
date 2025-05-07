# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2021-23
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can't redistribute/reshare/recreate it for any purpose.
#
#################################################################################

{

    'name': 'Setu Simplify Access Management',
    'version': '17.1',

    'sequence': 5,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com/',
    'support': 'support@setuconsulting.com',
    'license': 'OPL-1',
    'category': 'Tools',
    'summary': """All In One Access Management App for setting the correct access rights for fields, models, menus, views for any module and for any user.
        """,

    'description': """
	
    """,
    "images": ["static/description/banner.gif"],
    "price": "370.99",
    "currency": "USD",
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'data/view_data.xml',
        'views/access_management_view.xml',
        'views/res_users_view.xml',
        'views/store_model_nodes_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/simplify_access_management/static/src/js/action_menus.js',
            '/simplify_access_management/static/src/js/hide_chatter.js',
            '/simplify_access_management/static/src/js/cog_menu.js',
            '/simplify_access_management/static/src/js/form_controller.js',
            '/simplify_access_management/static/src/js/pivot_grp_menu.js',
            '/simplify_access_management/static/src/js/model_field_selector.js',
        ],

    },
    'depends': ['web', 'advanced_web_domain_widget'],
    'post_init_hook': 'post_install_action_dup_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
}
