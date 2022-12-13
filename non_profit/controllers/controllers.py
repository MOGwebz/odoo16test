# -*- coding: utf-8 -*-
# from odoo import http


# class NonProfit(http.Controller):
#     @http.route('/non_profit/non_profit', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/non_profit/non_profit/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('non_profit.listing', {
#             'root': '/non_profit/non_profit',
#             'objects': http.request.env['non_profit.non_profit'].search([]),
#         })

#     @http.route('/non_profit/non_profit/objects/<model("non_profit.non_profit"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('non_profit.object', {
#             'object': obj
#         })
