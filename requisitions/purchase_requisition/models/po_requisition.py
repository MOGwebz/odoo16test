from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons import decimal_precision as dp


import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_number = fields.Char('PO Requisition')
    requisition_id = fields.Many2one('po.requisition', 'Requisition')


class Requisition(models.Model):
    _name = "po.requisition"
    _inherit = ['mail.thread']

    @api.model
    def _po_count(self):
        attach = self.env['purchase.order']
        for po in self:
            domain = [('requisition_id', '=', self.id)]
            attach_ids = attach.search(domain)
            po_count = len(attach_ids)
            po.po_count = po_count
        return True

    @api.depends('order_line','order_line2')
    def _calc_po_total(self):
        for rec in self:
            total = 0
            for line in rec.order_line:
                total += line.total

            rec.total = total

    name = fields.Char('PO Requisition', default='/')
    requested_by = fields.Many2one('res.users', string="Requested By")
    user = fields.Many2one('res.users', 'Approved By')
    user_complete = fields.Many2one('res.users', 'Completed By')
    department_id = fields.Many2one('hr.department', string="Department")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, default=1)
    po_count = fields.Integer('RFQs/POs', compute=_po_count)
    total = fields.Float(string='Total', digits=dp.get_precision('Product Price'), compute="_calc_po_total", store=True)
    currency = fields.Many2one('res.currency', string="Currency")
    delivery_date = fields.Datetime(string='Expected Delivery Date', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted','Submited'),
        ('approved','Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='always')
    partner_id = fields.Many2one('res.partner', string='Vendor / Supplier', help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    order_line = fields.One2many('requisition.order.line', 'order_id', string='Order Lines', copy=True, track_visibility='always')
    order_line2 = fields.One2many('requisition.order.line', 'order_id', string='Order Lines', copy=True, track_visibility='always')
    purchase_order = fields.Many2one('purchase.order', string='Purchase Order')
    rejection_reason = fields.Text("Reason for Rejecting the Requisition")

    

    def submit_btn(self):
        if len(self.order_line) < 1:
            raise UserError(_('Please provide at least one item to be purchased!'))

        for line_item in self.order_line:
            if line_item.product_qty <= 0:
                raise UserError(_('Please the quantity for '+str(line_item.product_id.name)))

        self.write({
            'state': 'submitted',
            'requested_by': self.env.user.id,
            'department_id': self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False,
        })
        # self.send_hod_email_alert()
        # template_id = self.env.ref('project_status.nexus_purchase_order_requisition_email').id
        # self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)

    def submit_for_approval(self):
        self.write({
            'state': 'approved',
            'user': self.env.uid,
        })

    def action_approve_po_requisition(self):
        if len(self.order_line2) > 0:
            for rec in self:

                # if not rec.partner_id:
                #     raise UserError(_('Please add a vendor/spplier '))

                if rec.total <= 0:
                    raise UserError(_('Please provide the unit price for the items requested for!'))

                unique_ids = []
                for line_item in self.order_line2:
                    if not line_item.product_id:
                        raise UserError(_('Please Provide products for the PO Requisition'))
                    if not line_item.partner_id:
                        raise UserError(_('Please Add Vendor/Spplier for '+str(line_item.product_id.name)))
                    # if not line_item.currency:
                    #     raise UserError(_('Please Add Currency for ' + str(line_item.product_id.name)))

                    # Store vendors and currency as a key value pair
                    if not (line_item.partner_id.id in unique_ids):
                        unique_ids.append(line_item.partner_id.id)

                for key in unique_ids:
                    records = self.env['requisition.order.line'].search([('partner_id', '=', key), ('order_id', '=', rec.id)])
                    po_data = {
                        'requisition_number': str(rec.name),
                        'date_order': fields.datetime.now(),
                        'partner_id': key,
                        'requisition_id': rec.id,
                        # 'currency_id': value,
                    }
                    po_line_list = list()
                    for line in records:
                        # for line in rec.order_line:
                        po_line_list.append([0, False,
                            {
                                'name': line.product_id.product_tmpl_id.name + " " + line.name if line.name else line.product_id.product_tmpl_id.name,
                                'product_id': line.product_id.id,
                                'product_qty': line.product_qty,
                                'product_uom': line.product_uom.id,
                                'date_planned': fields.datetime.now(),
                                'price_unit': line.price_unit,
                        }])

                    po_data['order_line'] = po_line_list

                    # create PO
                    po_env = self.env['purchase.order'].create(po_data)

                    for line in records:
                        line.write({'purchase_order_id': po_env.id})

                rec.write({
                    'state': 'done',
                    'user_complete' : self.env.uid,
                    'purchase_order': po_env.id,
                })
                
        return True

    def cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def reject(self):
        for rec in self:
            rec.state = 'rejected'

    # @api.model
    def unlink(self):
        for rec in self:
            if rec.state in ('approved', 'done'):
                raise UserError(_("You can only delete records in Draft State or cancelled!"), _("Something is wrong!"), _("error"))
        return super(Requisition, self).unlink()

    @api.model
    def create(self, values):

        record = super(Requisition, self).create(values)
        record.name = "REQ0" + str(record.id)

        return record

class RequisitionOrderLine(models.Model):
    _name = 'requisition.order.line'
    _description = 'Requisition Order Line'

    @api.depends('product_qty', 'price_unit')
    def _calc_total(self):
        for rec in self:
            rec.total = rec.price_unit * rec.product_qty

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', related="order_id.state", index=True, store=True)

    order_id = fields.Many2one('po.requisition', string='Order Reference')
    name = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True,)
    
    @api.onchange('product_id')
    def set_description(self):
        for item in self:
            if item.product_id and not item.name:
                item.name = item.product_id.name

    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure', required=True, related="product_id.uom_po_id")
    price_unit = fields.Float(string='Price', digits=dp.get_precision('Product Price'))
    total = fields.Float(string='Total', digits=dp.get_precision('Product Price'), compute=_calc_total, store=True)
    partner_id = fields.Many2one('res.partner', string='Vendor / Supplier', help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    currency = fields.Many2one('res.currency', string="Currency")


    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
