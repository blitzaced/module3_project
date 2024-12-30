# Module 3 Project - E-commerce API |
# ----------------------------------

from flask import Flask, request, jsonify, Config
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, post_load
from sqlalchemy import Float, ForeignKey, Table, String, Column, select, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)

#MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Chip2447@localhost/ecommerce_api'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Creating the Base Model
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy and Marshmallow
db = SQLAlchemy()             # model_class = Base
db.init_app(app)
ma = Marshmallow(app)

# The association table between one User and multiple Orders (One-to-Many)
user_order = Table(
    "user_order",
    Base.metadata,
    Column("user_id", ForeignKey("user_account.id")),
    Column("order_id", ForeignKey("orders.id")),
)

# The association tablebetween multiple orders and multiple products (Many-to-Many)
order_product = Table(
    'order_product', 
    Base.metadata,
    Column('order_id', ForeignKey('orders.id'), primary_key=True),
    Column('product_id', ForeignKey('products.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)                                                                                 # MUST BE UNIQUE
    
    # One-to-Many relationship from this User to a List of Orders
    orders: Mapped[List["Order"]] = relationship("Order", back_populates = "user")
    

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[datetime] = mapped_column(DateTime)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))
    
    # Many-to-Many relationship between Orders and Products
    products: Mapped[List["Product"]] = relationship("Product", secondary = order_product, back_populates = "orders")
    
    user: Mapped["User"] = relationship("User", back_populates="orders")


class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), index=True)
    price: Mapped[float] = mapped_column(Float)                                                                                 
    
    # Many-to-Many relationship between Products and Orders
    orders: Mapped[List["Order"]] = relationship("Order", secondary = order_product, back_populates = "products")


# SCHEMAS
# -----------------------------------------------------------------------------------------------
# User Schema
class  UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        
# Order Schema
class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_fk=True

# Product Schema
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        
    @post_load
    def make_product(self, data, **kwargs):
        # Automatically map the 'name' field to 'product_name' before returning the data
        if 'name' in data:
            data['product_name'] = data.pop('name')
        return data

# Initialize Schemas     
user_schema = UserSchema()
users_schema = UserSchema(many = True)                      #Can serialize many User objects (a list of them)
order_schema = OrderSchema()
orders_schema = OrderSchema(many = True)                    #Can serialize many Order objects (a list of them)   
product_schema = ProductSchema()
products_schema = ProductSchema(many = True)                #Can serialize many Product objects (a list of them)    


# API ENDPOINTS/ROUTES --------------------------------------------------------------------------

# CREATE NEW USER
# -----------------------------------------------------------------------------------------------
@app.route('/users', methods = ['POST'])
def create_user():
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    existing_user = db.session.execute(select(User).where(User.email == user_data['email'])).scalars().first()
    
    if existing_user:
        return jsonify({"message": "Email is already in use."}), 400
    
    new_user = User(name = user_data['name'], email = user_data['email'], address = user_data.get('address', ''))
    db.session.add(new_user)
    db.session.commit()
    
    return user_schema.jsonify(new_user), 201


# READ ALL USERS
# -----------------------------------------------------------------------------------------------
@app.route('/users', methods = ['GET'])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()
    
    return users_schema.jsonify(users), 200


# READ A SINGLE USER BY ID
# -----------------------------------------------------------------------------------------------
@app.route('/users/<int:user_id>', methods = ['GET'])
def get_user(user_id):
    user = db.session.get(User, user_id)
    
    return user_schema.jsonify(user), 200


# UPDATE INDIVIDUAL USER BY ID
# -----------------------------------------------------------------------------------------------
@app.route('/users/<int:user_id>', methods = ['PUT'])
def update_user(user_id):
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({"message": "Invalid user id"}), 400
    
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    user.name = user_data['name']
    user.email = user_data['email']
    
    db.session.commit()
    return user_schema.jsonify(user), 200


# DELETE USER BY ID
# ------------------------------------------------------------------------------------------------
@app.route('/users/<int:user_id>', methods = ['DELETE'])
def delete_user(user_id):
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({"message": "Invalid user id"}), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"successfully deleted user {user_id}"}), 200 


# CREATE NEW ORDER (requires user ID and order date)
# -----------------------------------------------------------------------------------------------
@app.route('/orders', methods = ['POST'])
def create_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    if 'order_date' not in order_data or 'user_id' not in order_data:
        return jsonify({"message": "Order date and user ID are required."}), 400
    
    user = db.session.get(User, order_data['user_id'])
    if not user:
        return jsonify({"message": "Invalid user ID"})
    
    new_order = Order(order_date = order_data['order_date'], user_id = order_data['user_id'])
    db.session.add(new_order)
    db.session.commit()
    
    return order_schema.jsonify(new_order), 201


# ADD A PRODUCT TO AN ORDER (PREVENT DUPLICATES)
# -----------------------------------------------------------------------------------------------
@app.route('/orders/<int:order_id>/add_products/<int:product_id>', methods = ['POST'])
def add_products(order_id, product_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    order.products.append(product)
    db.session.commit()
        
    return jsonify({"message": "Product added!"}), 200


# REMOVE PRODUCT FROM AN ORDER
# ------------------------------------------------------------------------------------------------
@app.route('/orders/<int:order_id>/remove_product', methods = ['DELETE'])
def remove_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    if product in order.products:
        order.products.remove(product)
        db.session.commit()
        return jsonify({"message": "Product removed from order"}), 200
    else:
        return jsonify({"message": "Product not in this order"}), 400


# SHOW USER ORDERS
# -----------------------------------------------------------------------------------------------
@app.route('/orders/user/<int:user_id>', methods = ['GET'])
def user_orders(user_id):
    user = db.session.get(User, user_id)
    return orders_schema.jsonify(user.orders), 200


# SHOW ORDER PRODUCTS
# -----------------------------------------------------------------------------------------------
@app.route('/orders/<int:order_id>/products', methods = ['GET'])
def order_products(order_id):
    order = db.session.get(Order, order_id)
    return products_schema.jsonify(order.products), 200


# RETRIEVE ALL PRODUCTS
# -----------------------------------------------------------------------------------------------
@app.route('/products', methods = ['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()
    
    return products_schema.jsonify(products), 200


# READ A SINGLE USER BY ID
# -----------------------------------------------------------------------------------------------
@app.route('/products/<int:product_id>', methods = ['GET'])
def get_product(product_id):
    product = db.session.get(Product, product_id)
    
    return product_schema.jsonify(product), 200


# CREATE NEW PRODUCT
# -----------------------------------------------------------------------------------------------
@app.route('/products', methods = ['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    if 'product_name' not in product_data:
        return jsonify({"message": "Product name is required."}), 400
    
    new_product = Product(product_name = product_data['product_name'], price = product_data.get('price', 0.0))
    
    db.session.add(new_product)
    db.session.commit()
    
    return product_schema.jsonify(new_product), 201


# UPDATE A PRODUCT BY ID
# -----------------------------------------------------------------------------------------------
@app.route('/products/<int:product_id>', methods = ['PUT'])
def update_product(product_id):
    product = db.session.get(Product, product_id)
    
    if not product:
        return jsonify({"message": "Invalid product"}), 400
    
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']
        
    db.session.commit()
    return product_schema.jsonify(product), 200


# DELETE PRODUCT BY ID
# ------------------------------------------------------------------------------------------------
@app.route('/products/<int:product_id>', methods = ['DELETE'])
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    
    if not product:
        return jsonify({"message": "Invalid product"}), 400
    
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"successfully deleted product {product_id}"}), 200 


# LIST ALL AVAILABEL ROUTES
print("Available routes:")
for rule in app.url_map.iter_rules():
    print(rule)

# RUN
# ------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    
    with app.app_context():
        db.create_all()
                
    app.run(debug=True)