"""
Payment Service - Manages payments and billing
"""

from datetime import datetime
import uuid

class PaymentService:
    """
    Service for managing payments and billing
    Handles payment processing, invoices, and transaction history
    """
    
    def __init__(self):
        self.payments_db = []
        self.invoices_db = []
        self.service_prices = self._initialize_prices()
    
    def _initialize_prices(self):
        """Initialize service prices"""
        return {
            'consultation': 50.00,
            'lab_test_fasting_glucose': 25.00,
            'lab_test_hba1c': 45.00,
            'lab_test_ogtt': 60.00,
            'lab_test_insulin': 55.00,
            'prediction_service': 30.00,
            'prescription': 15.00,
            'follow_up': 35.00
        }
    
    def calculate_total(self, items):
        """
        Calculate total amount for services
        
        Args:
            items: list of service items
        
        Returns:
            dict with total calculation
        """
        total = 0
        breakdown = []
        
        for item in items:
            service = item.get('service')
            price = self.service_prices.get(service, 0)
            quantity = item.get('quantity', 1)
            subtotal = price * quantity
            
            breakdown.append({
                'service': service,
                'price': price,
                'quantity': quantity,
                'subtotal': subtotal
            })
            
            total += subtotal
        
        # Add tax (if applicable)
        tax = total * 0.10  # 10% tax
        grand_total = total + tax
        
        return {
            'success': True,
            'subtotal': total,
            'tax': tax,
            'grand_total': grand_total,
            'breakdown': breakdown,
            'currency': 'USD'
        }
    
    def create_invoice(self, patient_id, items, due_date=None):
        """
        Create an invoice for patient
        
        Args:
            patient_id: ID of the patient
            items: list of service items
            due_date: payment due date
        
        Returns:
            dict with invoice details
        """
        calculation = self.calculate_total(items)
        
        if not due_date:
            from datetime import timedelta
            due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        invoice = {
            'invoice_id': f"INV{len(self.invoices_db) + 1:06d}",
            'patient_id': patient_id,
            'created_date': datetime.now().isoformat(),
            'due_date': due_date,
            'items': items,
            'subtotal': calculation['subtotal'],
            'tax': calculation['tax'],
            'grand_total': calculation['grand_total'],
            'status': 'pending',
            'payments': []
        }
        
        self.invoices_db.append(invoice)
        
        return {
            'success': True,
            'invoice': invoice,
            'message': 'Invoice created successfully'
        }
    
    def process_payment(self, patient_id, amount, payment_method, invoice_id=None):
        """
        Process a payment
        
        Args:
            patient_id: ID of the patient
            amount: payment amount
            payment_method: method of payment
            invoice_id: optional invoice ID
        
        Returns:
            dict with payment result
        """
        # Generate unique transaction ID
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        
        payment = {
            'payment_id': f"PAY{len(self.payments_db) + 1:06d}",
            'transaction_id': transaction_id,
            'patient_id': patient_id,
            'invoice_id': invoice_id,
            'amount': amount,
            'payment_method': payment_method,
            'status': 'completed',
            'date': datetime.now().isoformat()
        }
        
        self.payments_db.append(payment)
        
        # Update invoice if provided
        if invoice_id:
            for invoice in self.invoices_db:
                if invoice['invoice_id'] == invoice_id:
                    invoice['payments'].append(payment)
                    
                    # Check if fully paid
                    total_paid = sum(p['amount'] for p in invoice['payments'])
                    if total_paid >= invoice['grand_total']:
                        invoice['status'] = 'paid'
                    else:
                        invoice['status'] = 'partial'
                    break
        
        return {
            'success': True,
            'payment': payment,
            'receipt': self._generate_receipt(payment),
            'message': 'Payment processed successfully'
        }
    
    def _generate_receipt(self, payment):
        """Generate a receipt for payment"""
        receipt = f"""
╔══════════════════════════════════════════════════════════════╗
║                     PAYMENT RECEIPT                           ║
╠══════════════════════════════════════════════════════════════╣
║  Receipt No: {payment['payment_id']}                                  
║  Transaction ID: {payment['transaction_id']}                           
║  Date: {payment['date'][:10]}                                          
║  Time: {payment['date'][11:19]}                                          
╠══════════════════════════════════════════════════════════════╣
║  Amount: ${payment['amount']:.2f}                                         
║  Payment Method: {payment['payment_method']}                                   
║  Status: {payment['status']}                                                 
╠══════════════════════════════════════════════════════════════╣
║  Thank you for your payment!                                  ║
║  This is a computer-generated receipt.                        ║
╚══════════════════════════════════════════════════════════════╝
        """
        return receipt
    
    def get_patient_payments(self, patient_id):
        """
        Get payment history for a patient
        
        Args:
            patient_id: ID of the patient
        
        Returns:
            list of payments
        """
        payments = [p for p in self.payments_db if p['patient_id'] == patient_id]
        
        total_spent = sum(p['amount'] for p in payments)
        
        return {
            'success': True,
            'payments': payments,
            'count': len(payments),
            'total_spent': total_spent
        }
    
    def get_patient_invoices(self, patient_id):
        """
        Get invoices for a patient
        
        Args:
            patient_id: ID of the patient
        
        Returns:
            list of invoices
        """
        invoices = [i for i in self.invoices_db if i['patient_id'] == patient_id]
        
        pending_total = sum(i['grand_total'] for i in invoices if i['status'] != 'paid')
        paid_total = sum(i['grand_total'] for i in invoices if i['status'] == 'paid')
        
        return {
            'success': True,
            'invoices': invoices,
            'count': len(invoices),
            'pending_total': pending_total,
            'paid_total': paid_total
        }
    
    def get_outstanding_balance(self, patient_id):
        """
        Get outstanding balance for a patient
        
        Args:
            patient_id: ID of the patient
        
        Returns:
            dict with balance information
        """
        invoices = [i for i in self.invoices_db if i['patient_id'] == patient_id]
        
        total_billed = sum(i['grand_total'] for i in invoices)
        total_paid = sum(p['amount'] for p in self.payments_db if p['patient_id'] == patient_id)
        
        outstanding = total_billed - total_paid
        
        return {
            'success': True,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'outstanding': max(0, outstanding),
            'currency': 'USD'
        }
    
    def refund_payment(self, payment_id, reason):
        """
        Process a refund
        
        Args:
            payment_id: ID of the payment
            reason: reason for refund
        
        Returns:
            dict with refund result
        """
        for payment in self.payments_db:
            if payment['payment_id'] == payment_id:
                payment['status'] = 'refunded'
                payment['refund_date'] = datetime.now().isoformat()
                payment['refund_reason'] = reason
                
                return {
                    'success': True,
                    'payment': payment,
                    'message': f'Refund processed for {payment["amount"]}'
                }
        
        return {'success': False, 'error': 'Payment not found'}