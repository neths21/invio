from app import db
from app.models.models import Product, Notification, InventoryTransaction, Supplier
from app.services.ai_service import AIService
from sqlalchemy import func
from datetime import datetime, timedelta

class NotificationService:
    def __init__(self):
        self.ai_service = AIService()
    
    def check_low_stock(self):
        """Check for products with low stock and generate notifications"""
        # Find products where quantity is below reorder level
        low_stock_products = Product.query.filter(
            Product.quantity_in_stock <= Product.reorder_level
        ).all()
        
        created_notifications = []
        
        for product in low_stock_products:
            # Check if a notification already exists for this product
            existing_notification = Notification.query.filter_by(
                product_id=product.id,
                notification_type='low_stock',
                is_read=False
            ).first()
            
            if not existing_notification:
                supplier = Supplier.query.get(product.supplier_id)
                
                # Generate AI notification message
                ai_message = self.ai_service.generate_low_stock_notification(product, supplier)
                
                # Create notification
                notification = Notification(
                    product_id=product.id,
                    notification_type='low_stock',
                    message=f"Low stock alert for {product.name}. Current stock: {product.quantity_in_stock}, Reorder level: {product.reorder_level}",
                    ai_summary=ai_message
                )
                
                db.session.add(notification)
                created_notifications.append(notification)
        
        if created_notifications:
            db.session.commit()
        
        return created_notifications
    
    def check_irregular_activity(self, days=7):
        """Check for irregular inventory activity"""
        # Get transactions from the last X days
        recent_date = datetime.utcnow() - timedelta(days=days)
        recent_transactions = InventoryTransaction.query.filter(
            InventoryTransaction.transaction_date >= recent_date
        ).all()
        
        created_notifications = []
        
        # Get average transaction quantities by product and type
        product_avgs = {}
        for transaction in recent_transactions:
            key = (transaction.product_id, transaction.transaction_type)
            if key not in product_avgs:
                product_avgs[key] = {'total': 0, 'count': 0, 'transactions': []}
            
            product_avgs[key]['total'] += transaction.quantity
            product_avgs[key]['count'] += 1
            product_avgs[key]['transactions'].append(transaction)
        
        # Calculate averages
        for key, data in product_avgs.items():
            if data['count'] > 1:  # Need at least 2 transactions to detect irregularities
                avg_quantity = data['total'] / data['count']
                
                for transaction in data['transactions']:
                    # Check if transaction is significantly different from average
                    deviation_threshold = 2.0  # 200% above average or 50% below average
                    deviation = transaction.quantity / avg_quantity if avg_quantity > 0 else 0
                    
                    is_irregular = deviation > deviation_threshold or (deviation > 0 and deviation < (1/deviation_threshold))
                    
                    if is_irregular:
                        # Check if notification already exists for this transaction
                        existing_notification = Notification.query.filter_by(
                            product_id=transaction.product_id,
                            notification_type='irregular_activity',
                            is_read=False
                        ).first()
                        
                        if not existing_notification:
                            product = Product.query.get(transaction.product_id)
                            
                            # Generate AI alert message
                            ai_message = self.ai_service.generate_irregular_activity_alert(
                                product, transaction, avg_quantity
                            )
                            
                            # Create notification
                            notification = Notification(
                                product_id=transaction.product_id,
                                notification_type='irregular_activity',
                                message=f"Irregular activity detected for {product.name}. Transaction quantity: {transaction.quantity}, Average: {avg_quantity:.2f}",
                                ai_summary=ai_message
                            )
                            
                            db.session.add(notification)
                            created_notifications.append(notification)
        
        if created_notifications:
            db.session.commit()
        
        return created_notifications
