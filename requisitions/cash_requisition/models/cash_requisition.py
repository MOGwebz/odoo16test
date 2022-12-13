from datetime import datetime, timedelta, date
from odoo import models, fields, api, _

class AcocuntMove(models.Model):
    _inherit = "account.move"

    requisition_id = fields.Many2one('cash.request', 'Cash Requisition')

class CashRequest(models.Model):
    _name = 'cash.request'
    _description = 'Cash requisition Form'
    _order = 'create_date desc'


    STATUS = [
        ('draft', 'Draft'),
        ('submitted','Submitted'),
        ('approved', 'Approved'),
        ('cash_out', 'Cash Out'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'), 
    ]

    def _get_current_date(self):
        """ :return current date """
        return fields.Date.today()

   

    # @api.model
    # def _get_partner(self):
    #     """Return default physician value"""
    #     hr_obj = self.env['res.partner']
    #     domain = [('user_id', '=', self.env.uid)]
    #     user_ids = hr_obj.search(domain, limit=1)
    #     if user_ids:
    #         return user_ids.id or False
    #     else:
    #         return False

    # @api.model
    # def _default_journal(self):
    #     jrnl = self.env['account.journal'].search([('name', 'ilike', 'Cash')])
    #     return jrnl

    name = fields.Char('Name', default="/")
    requested_by = fields.Many2one('res.users', string="Requested By")
    department_id = fields.Many2one('hr.department', string="Department")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor')
    amount = fields.Float('Amount Requested', compute='_get_total')
    date = fields.Date('Date Requested')
    user = fields.Many2one('res.users', 'Approved By')
    acc_id = fields.Many2one('account.move')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=1)
    approval_date = fields.Date('Approval Date')
    state = fields.Selection(STATUS, default='draft')
    notes = fields.Text('Reject Reason')
    line_ids = fields.One2many('cash.request.lines', 'cash_id')


    @api.depends('line_ids.total_price')
    def _get_total(self):
        for move in self:
            total = 0.0
            for line in move.line_ids:
                total += line.total_price
            move.amount = total

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('cash.request')
        vals['name'] = sequence
        res = super(CashRequest, self).create(vals)
        return res

    def btn_mv_submitted(self):
        for rec in self:
            if rec.amount <= 0.00:
                raise models.ValidationError('Cannot request for zero (0) amounts of money!!!')
            else:
                rec.write({
                    'requested_by' : self.env.uid,
                    'department_id' : self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False,
                    'state': 'submitted',
                    'date': date.today(),
                })
                # rec.send_hod_email_alert()

    def reject_request(self):
        """
        This Method is used to reject a requisition.
        """
        for data in self:
            data.write({
                'state': 'reject'
            })

    def cancel_request(self):
        """
        This Method is used to cancel a requisition.
        """
        for data in self:
            data.write({
                'state': 'cancel'
            })

    def reset_request(self):
        """
        This Method is used to reset a requisition.
        """
        for data in self:
            data.write({
                'state': 'draft'
            })

    def approve_request(self):
        """
        This Method is used to approve a requisition.
        """
        for data in self:
            data.write({'state': 'cash_out'})
            data.approval_date = str(datetime.now())
            data.user = self.env.uid

    def _default_account(self):
        journal = self.env['account.journal'].search(
            [('type', '=', 'purchase')], limit=1)
        return journal.default_account_id.id

    def cash_request(self):
        """
        This Method is used to cash out a requisition.
        """
        pay_obj = self.env['account.move']

        if self.amount <= 0.00:
            raise models.ValidationError('You cannot Make a payment of amount Zero(0)')
        for data in self:
            if not data.user:
                raise models.ValidationError('Cannot make this payment. you need approval')
            else:
                prd_account_id = self._default_account()

                inv_lines = []
                for rec in data.line_ids:
                    inv_line_values = {
                        'name': "Requisition for " + rec.item,
                        'quantity': 1,
                        'account_id': prd_account_id,
                        'price_unit': rec.unit_price,
                        'account_id': rec.account_id.id,
                    }
                    inv_lines.append((0, 0, inv_line_values))

                inv_values = {
                    'move_type': 'in_receipt',
                    'requisition_id': self.id,
                    'partner_id': data.requested_by.partner_id.id,
                    'invoice_date': data.date,
                    'invoice_line_ids': inv_lines
                }
                acc_id = pay_obj.create(inv_values)
                data.write({'acc_id': acc_id.id})
                acc_id.action_post()

            self.write({'state': 'done'})
        return 0

    # def open_invoice(self):
    #     """
    #     This Method is used to Open invoice from Patient record.
    #     @param self: The object pointer
    #     """
    #     if not self.invc_id:
    #         raise models.ValidationError(_('There isnt any invoice Created, please check with Administrator'))
    #
    #     context = dict(self._context or {})
    #     wiz_form_id = self.env['ir.model.data'].get_object_reference(
    #         'account_voucher', 'view_purchase_receipt_form')[1]
    #     return {
    #         'view_type': 'form',
    #         'view_id': wiz_form_id,
    #         'view_mode': 'form',
    #         'res_model': 'account.move',
    #         'res_id': self.invc_id.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #         'context': context,
    #     }


class CashRequestLines(models.Model):
    _name = 'cash.request.lines'
    _description = "Requisition Lines"


    cash_id = fields.Many2one('cash.request')
    item = fields.Char('Items')
    description = fields.Text("Description")
    qty = fields.Float("Quantity", default=1.0)
    unit_price = fields.Float('Unit Price')
    total_price = fields.Float('Total Amount', compute='_get_total')
    account_id = fields.Many2one('account.account', 'Account')
    # attachment = fields.Many2one('ir.attachment', string="Attachment", tracking=True)

    @api.depends('qty', 'unit_price')
    def _get_total(self):
        for rec in self:
            ttl = 0.0
            ttl = rec.qty * rec.unit_price
            rec.total_price = ttl
