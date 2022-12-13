# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date


class NonProfit(models.Model):
    _name = 'non.profit'
    _inherit = ['mail.thread', 'mail.activity.mixin',]
    _description = 'Module for Non Profits Funds Request'

    name = fields.Char(string="Ref#", default="/")
    value = fields.Integer()
    journal_id = fields.Many2one('account.journal', string="Method of payment", domain=[('type', 'in', ('bank', 'cash'))])
    journal_entry_id = fields.Many2one('account.move',string="Journal Entry", copy=False)
    description = fields.Text()
    donor = fields.Many2one('res.partner', 'Donor', domain="[('donor', '=', True)]")
    amount = fields.Monetary('Amount', tracking=True)
    payment = fields.Many2one('account.payment', 'Payment',)
    donor_income_account = fields.Many2one('account.account', 'Donor Income Account')
    currency_id = fields.Many2one('res.currency', tracking=True, string='Currency', default=lambda self: self.env.user.company_id.currency_id.id)
    status = fields.Selection([
        ('draft', "Draft"),
        ('confirm', "Validated"),
        ('complete', "Done"),
        ('cancel', "Canceled"),
    ], readonly=True, string="Status", tracking=True, default='draft')

    def request_confirm(self):
        for rec in self:
            rec.status = 'confirm'
    
    def request_cancel(self):
        for rec in self:
            rec.status = 'cancel'

    def process_payment(self):
        account_move = self.env["account.move"]
        for rec in self:
            name_of = rec.donor.name
            int_debit_line = [0,0,{'account_id' : rec.journal_id.inbound_payment_method_line_ids[0].payment_account_id.id,
                    'partner_id' : rec.donor.id,
                    'name' : 'Funds from ' + name_of,
                    'debit' : rec.amount,
                    'credit' : 0.0
                    }]


            int_credit_line = [0,0,{'account_id' :  rec.donor_income_account.id,
                                'partner_id' : rec.donor.id,
                                'name' : 'Funds from ' + name_of,
                                'debit' : 0.0,
                                'credit' : rec.amount
                                }]

            int_move_line = [int_debit_line,int_credit_line]

            int_jounral = account_move.create({
                        'date': date.today(),
                        'journal_id' :rec.journal_id.id,
                        'ref' : str(rec.name) ,
                        'line_ids' : int_move_line})

            int_jounral.action_post()
            rec.journal_entry_id = int_jounral.id
            self.write({'status':'complete'})

    # def process_payment(self):
    #     for rec in self:
    #         context = dict({
    #             'default_payment_type':'inbound',
	# 			# 'default_partner_type': 'customer',
	# 			'default_ref': rec.name,
	# 			'default_date':date.today(),
	# 			'default_amount':rec.amount,
    #             # 'default_journal_id': rec.source_journal.id,
    #             'default_currency_id':rec.currency_id.id,
    #             'default_partner_id': self.donor.id,
	# 			'default_fund_request': rec.id,
    #             'default_destination_account_id': rec.donor_income_account.id,

    #         })

    #         wiz_form_id = self.env['ir.model.data']._xmlid_lookup('account.view_account_payment_form')[2]
    #         return {                    
	# 			'view_id': wiz_form_id,
	# 			'view_mode': 'form',
    #             'views': [(wiz_form_id, 'form')],
	# 			'res_model': 'account.payment',
	# 			'type': 'ir.actions.act_window',
	# 			'target': 'new',
	# 			'context': context,
	# 		}

    @api.model
    def create(self, vals):

        sequence = self.env['ir.sequence'].next_by_code('non.profit')
        vals['name'] = sequence
        res = super(NonProfit,self).create(vals)

        return res

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    fund_request = fields.Many2one('non.profit', 'Fund Request',)

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        if self.fund_request:
            self.fund_request.write({'status' : 'complete'})
        return res

    @api.onchange('fund_request')
    def change_account(self):
        for rec in self:
            rec.destination_account_id = rec.fund_request.donor_income_account.id

    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        if res.fund_request:            
            res.fund_request.write({'payment' : res.id})
        return res

class NonProfitPartner(models.Model):
    _inherit = 'res.partner'

    donor = fields.Boolean('Donor')

