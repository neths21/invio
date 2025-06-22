from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    TextAreaField, FloatField, IntegerField, SelectField,
    DateTimeField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
from datetime import datetime
from app.models.models import Product
from wtforms.fields import DateTimeLocalField
# Authentication forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Inventory forms
class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    sku = StringField('SKU', validators=[DataRequired(), Length(max=50)])
    unit_price = FloatField('Unit Price', validators=[DataRequired(), NumberRange(min=0)])
    quantity_in_stock = IntegerField('Quantity in Stock', validators=[DataRequired(), NumberRange(min=0)])
    reorder_level = IntegerField('Reorder Level', validators=[DataRequired(), NumberRange(min=0)])
    reorder_quantity = IntegerField('Reorder Quantity', validators=[DataRequired(), NumberRange(min=1)])
    category_id = SelectField('Category', validators=[DataRequired()], coerce=int)
    supplier_id = SelectField('Supplier', validators=[DataRequired()], coerce=int)
    submit = SubmitField('Save')

    def validate_sku(self, field):
        # Check if we're editing an existing product or creating a new one
        if hasattr(self, 'product_id'):
            # For editing: check if another product has this SKU
            product = Product.query.filter(
                Product.sku == field.data,
                Product.id != self.product_id
            ).first()
        else:
            # For new product: check if any product has this SKU
            product = Product.query.filter_by(sku=field.data).first()
        
        if product:
            raise ValidationError('This SKU is already in use. Please enter a unique SKU.')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=64)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Save')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=100)])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Save')

class InventoryTransactionForm(FlaskForm):
    product_id = SelectField('Product', validators=[DataRequired()], coerce=int)
    transaction_type = SelectField('Transaction Type', 
                                   choices=[
                                       ('purchase', 'Purchase'), 
                                       ('sale', 'Sale'), 
                                       ('adjustment', 'Adjustment')
                                   ],
                                   validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = FloatField('Unit Price', validators=[DataRequired(), NumberRange(min=0)])
    transaction_date = DateTimeLocalField('Transaction Date', default=datetime.now, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')

class PurchaseOrderForm(FlaskForm):
    supplier_id = SelectField('Supplier', validators=[DataRequired()], coerce=int)
    order_date = DateTimeField('Order Date', default=datetime.now, format='%Y-%m-%d', validators=[DataRequired()])
    expected_delivery_date = DateTimeField('Expected Delivery Date', format='%Y-%m-%d', validators=[Optional()])
    status = SelectField('Status', 
                        choices=[
                            ('pending', 'Pending'),
                            ('approved', 'Approved'),
                            ('received', 'Received'),
                            ('canceled', 'Canceled')
                        ],
                        default='pending',
                        validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')
