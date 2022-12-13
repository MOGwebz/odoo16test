# -*- coding: utf-8 -*-
{
    'name': "non_profit",

    'summary': """
        Module to Manage Non Profit Organisations""",

    'description': """
         Module to Manage Non Profit Organisations
    """,

    'author': "TechThings",
    'website': "https://www.techthings.it",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'project', 'purchase',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/sequences.xml',
        'views/res_partner.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
