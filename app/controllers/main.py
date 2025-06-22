from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.models import Notification, Product, Category, Supplier, InventoryTransaction, PurchaseOrder
from app.services.notification_service import NotificationService
from app import db
import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    # Get the time period filter from query parameters (default to 'week')
    time_period = request.args.get('period', 'week')
    
    # Get counts for dashboard
    product_count = Product.query.count()
    category_count = Category.query.count()
    supplier_count = Supplier.query.count()
    
    # Calculate date ranges based on the selected period
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if time_period == 'today':
        start_date = today
        end_date = today + datetime.timedelta(days=1)
    elif time_period == 'week':
        # Start from the beginning of current week (Monday)
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = start_date + datetime.timedelta(days=7)
    elif time_period == 'month':
        # Start from the beginning of current month
        start_date = today.replace(day=1)        # Go to the first day of next month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1)
    elif time_period == 'year':
        # Start from the beginning of current year
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(year=today.year + 1, month=1, day=1)
    else:  # fallback to week if invalid period is provided
        # Start from the beginning of current week (Monday)
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = start_date + datetime.timedelta(days=7)
      # Filter transactions by date range
    transaction_count = InventoryTransaction.query.filter(
        InventoryTransaction.transaction_date >= start_date,
        InventoryTransaction.transaction_date < end_date
    ).count()
    
    # Get recent transactions within the date range
    recent_transactions = InventoryTransaction.query.filter(
        InventoryTransaction.transaction_date >= start_date,
        InventoryTransaction.transaction_date < end_date
    ).order_by(InventoryTransaction.transaction_date.desc()).limit(5).all()
    
    # Get recent purchase orders within the date range
    recent_purchase_orders = PurchaseOrder.query.filter(
        PurchaseOrder.order_date >= start_date,
        PurchaseOrder.order_date < end_date
    ).order_by(PurchaseOrder.order_date.desc()).limit(5).all()
    
    # Get low stock products
    low_stock_products = Product.query.filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).limit(5).all()
    
    # Get unread notifications count
    notification_count = Notification.query.filter_by(is_read=False).count()
    
    # Check for new low stock items and notifications
    notification_service = NotificationService()
    notification_service.check_low_stock()
    notification_service.check_irregular_activity()
    
    # Get latest notifications
    notifications = Notification.query.order_by(
        Notification.created_at.desc()
    ).limit(5).all()
      # Prepare chart data for stock in/out trends by month
    from sqlalchemy import func, extract
    
    # For chart data, use the year view for yearly data, otherwise use the filtered date range
    if time_period == 'year':
        current_year = datetime.datetime.now().year
        
        # Get stock in transactions grouped by month for the current year
        stock_in_data = db.session.query(
            extract('month', InventoryTransaction.transaction_date).label('month'),
            func.sum(InventoryTransaction.quantity).label('total')
        ).filter(
            extract('year', InventoryTransaction.transaction_date) == current_year,
            InventoryTransaction.transaction_type == 'purchase'
        ).group_by('month').order_by('month').all()
        
        # Get stock out transactions grouped by month for the current year
        stock_out_data = db.session.query(
            extract('month', InventoryTransaction.transaction_date).label('month'),
            func.sum(InventoryTransaction.quantity).label('total')
        ).filter(
            extract('year', InventoryTransaction.transaction_date) == current_year,
            InventoryTransaction.transaction_type == 'sale'
        ).group_by('month').order_by('month').all()
        
        # Initialize arrays with zeros for all 12 months
        stock_in_by_month = [0] * 12
        stock_out_by_month = [0] * 12
        
        # Fill in the actual data
        for month, total in stock_in_data:
            stock_in_by_month[int(month)-1] = int(total)
        
        for month, total in stock_out_data:
            stock_out_by_month[int(month)-1] = int(total)
            
        chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    else:
        # For shorter time periods, create daily chart data
        if time_period == 'today':
            days = 24  # 24 hours
            date_format = '%H:%M'  # Hour format for today
        elif time_period == 'week':
            days = 7
            date_format = '%a'  # Day name for week
        elif time_period == 'month':
            days = 30
            date_format = '%d'  # Day of month
        
        # Generate date range for the chart
        chart_dates = []
        chart_labels = []
        
        if time_period == 'today':
            # For today, use hourly intervals
            for i in range(days):
                hour_date = today.replace(hour=i)
                chart_dates.append(hour_date)
                chart_labels.append(hour_date.strftime(date_format))
        else:
            # For week/month, use daily intervals
            for i in range(days):
                day_date = start_date + datetime.timedelta(days=i)
                chart_dates.append(day_date)
                chart_labels.append(day_date.strftime(date_format))
        
        # Initialize data arrays
        stock_in_by_day = [0] * days
        stock_out_by_day = [0] * days
        
        # For daily data in "today" view, group by hour
        if time_period == 'today':
            stock_in_data = db.session.query(
                extract('hour', InventoryTransaction.transaction_date).label('hour'),
                func.sum(InventoryTransaction.quantity).label('total')
            ).filter(
                InventoryTransaction.transaction_date >= start_date,
                InventoryTransaction.transaction_date < end_date,
                InventoryTransaction.transaction_type == 'purchase'
            ).group_by('hour').all()
            
            stock_out_data = db.session.query(
                extract('hour', InventoryTransaction.transaction_date).label('hour'),
                func.sum(InventoryTransaction.quantity).label('total')
            ).filter(
                InventoryTransaction.transaction_date >= start_date,
                InventoryTransaction.transaction_date < end_date,
                InventoryTransaction.transaction_type == 'sale'
            ).group_by('hour').all()
            
            # Fill hourly data
            for hour, total in stock_in_data:
                hour_idx = int(hour)
                if 0 <= hour_idx < len(stock_in_by_day):
                    stock_in_by_day[hour_idx] = int(total)
            
            for hour, total in stock_out_data:
                hour_idx = int(hour)
                if 0 <= hour_idx < len(stock_out_by_day):
                    stock_out_by_day[hour_idx] = int(total)
        else:
            # Group by day for week and month views
            stock_in_data = db.session.query(
                func.date(InventoryTransaction.transaction_date).label('day'),
                func.sum(InventoryTransaction.quantity).label('total')
            ).filter(
                InventoryTransaction.transaction_date >= start_date,
                InventoryTransaction.transaction_date < end_date,
                InventoryTransaction.transaction_type == 'purchase'
            ).group_by('day').all()
            
            stock_out_data = db.session.query(
                func.date(InventoryTransaction.transaction_date).label('day'),
                func.sum(InventoryTransaction.quantity).label('total')
            ).filter(
                InventoryTransaction.transaction_date >= start_date,
                InventoryTransaction.transaction_date < end_date,
                InventoryTransaction.transaction_type == 'sale'
            ).group_by('day').all()
            
            # Map dates to indexes
            date_to_index = {date.strftime('%Y-%m-%d'): i for i, date in enumerate(chart_dates)}
            
            # Fill daily data
            for day_date, total in stock_in_data:
                day_str = day_date.strftime('%Y-%m-%d')
                if day_str in date_to_index:
                    stock_in_by_day[date_to_index[day_str]] = int(total)
            
            for day_date, total in stock_out_data:
                day_str = day_date.strftime('%Y-%m-%d')
                if day_str in date_to_index:
                    stock_out_by_day[date_to_index[day_str]] = int(total)
        
        # Use the daily data for the chart
        stock_in_by_month = stock_in_by_day
        stock_out_by_month = stock_out_by_day
    
    return render_template(
        'dashboard.html',
        product_count=product_count,
        category_count=category_count,
        supplier_count=supplier_count,
        transaction_count=transaction_count,
        low_stock_products=low_stock_products,
        notification_count=notification_count,
        notifications=notifications,
        recent_transactions=recent_transactions,
        recent_purchase_orders=recent_purchase_orders,
        stock_in_by_month=stock_in_by_month,
        stock_out_by_month=stock_out_by_month,
        chart_labels=chart_labels,
        active_period=time_period
    )

@main_bp.route('/notifications')
@login_required
def notifications():
    # Get all notifications
    notifications = Notification.query.order_by(
        Notification.is_read,
        Notification.created_at.desc()
    ).all()
    
    return render_template('notifications.html', notifications=notifications)

@main_bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    
    return redirect(url_for('main.notifications'))
