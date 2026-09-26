# FreshCart

> A full-stack e-commerce platform built with Django, integrating inventory management, business intelligence, and machine-learning-based sales and inventory prediction.

## Overview

**FreshCart** is an academic full-stack e-commerce project designed to combine web development, database management, data analytics, and machine learning into a single application.

The platform provides two distinct interfaces:

* **Customer** — browse products, manage a cart, checkout, place orders, and view order history.
* **Admin** — manage products, categories, customers, orders, inventory, analytics, and ML predictions.

The project also includes historical sales-data generation so that the analytics and machine-learning components can be demonstrated with realistic data.

---

## Key Features

### Customer

* User registration and authentication
* Login/logout
* Product browsing
* Category-based product filtering
* Product details
* Shopping cart
* Quantity management
* Stock availability validation
* Out-of-stock handling
* Dynamic inventory-based pricing/discount display
* Checkout
* Delivery address selection

  * Manual address entry
  * Map-based location selection
* Cash on Delivery
* Dummy online payment interface
* Order confirmation
* Order history
* Customer account management

### Admin

* Admin authentication
* Admin dashboard
* Product management

  * Add products
  * Edit products
  * Delete products
  * Search products
  * Category filtering
* Category management
* Customer management
* Order management
* Inventory/stock management
* Stock batch management
* Stock expiry tracking
* Inventory availability monitoring
* Sales analytics
* Sales prediction
* Inventory prediction
* Reorder recommendations

---

## Inventory Management

FreshCart uses a stock-batch-based inventory system rather than treating all incoming stock as one undifferentiated quantity.

Each stock batch can track information such as:

* Product
* Quantity
* Remaining quantity
* Received date
* Expiry date
* Shelf-life information
* Batch-specific pricing/discount information

The system supports inventory consumption based on the age of available stock so that older inventory is consumed before newer inventory.

This allows FreshCart to model real-world grocery inventory where products such as milk, bread, fruits, and vegetables have different shelf lives.

### Expiry-Based Discounts

Products approaching expiry can receive a discount based on the relevant stock batch.

The customer-facing interface displays:

* Current discounted price
* Original price with strikethrough styling
* Discount percentage

This allows products approaching expiry to be sold at a reduced price instead of simply becoming unsellable inventory.

---

## Business Intelligence

FreshCart contains an admin-facing **Sales Analytics** module using Plotly.

Analytics include:

* Total sales/revenue
* Delivered orders
* Average order value
* Daily sales
* Monthly sales
* Yearly sales
* Product sales
* Category-level analysis
* Top-selling products
* Quantity sold

The analytics module uses historical order data to provide a business-oriented view of FreshCart's performance.

---

## Machine Learning

FreshCart includes machine-learning functionality through the `ml_prediction` application.

### Sales Prediction

The sales prediction system uses:

* Python
* Pandas
* Scikit-learn
* Random Forest Regression

Historical sales data is transformed into time-based features including:

* Day number
* Day of week
* Month
* Weekend indicator
* Previous-day demand
* Seven-day lag
* Rolling demand statistics

The model produces a short-term product demand forecast.

The prediction results can be used to understand expected future product demand and support inventory planning.

### Inventory Prediction

The inventory prediction system combines current inventory information with predicted demand.

It provides information such as:

* Current stock
* Predicted demand
* Expected stock after predicted demand
* Recommended reorder quantity
* Inventory status

Possible inventory conditions include:

* Out of Stock
* Reorder Required
* Low Stock
* Stock Sufficient

This connects the machine-learning component with the operational inventory-management component of the application.

---

## Historical Demo Data

FreshCart includes a Django management command:

```text
orders/management/commands/populate_sales.py
```

This command generates simulated historical sales data for demonstration and testing.

It is useful when the database does not yet contain enough real orders for:

* Sales Analytics
* Sales Prediction
* Inventory Prediction
* Product-level sales analysis

The generated data uses product demand patterns and randomized daily sales behavior to create a more realistic demonstration dataset.

### Run the data generator

```bash
python manage.py populate_sales
```

Make sure products have already been created before running the command.

---

## Technology Stack

### Backend

* Python
* Django

### Frontend

* HTML
* CSS
* JavaScript
* Bootstrap

### Database

* PostgreSQL support
* Django ORM

### Data Science / Machine Learning

* Pandas
* NumPy
* Scikit-learn
* Random Forest
* Feature engineering
* Time-series demand features

### Data Visualization

* Plotly

### Other

* Pillow
* python-dotenv

---

## Project Structure

```text
FreshCart/
│
├── manage.py
│
├── config/
│   └── Django project configuration
│
├── accounts/
│   └── Authentication and user accounts
│
├── products/
│   └── Products, categories and inventory
│
├── cart/
│   └── Shopping cart functionality
│
├── orders/
│   ├── Checkout and orders
│   └── management/
│       └── commands/
│           └── populate_sales.py
│
├── dashboard/
│   └── Admin dashboard, management and analytics
│
├── ml_prediction/
│   └── Sales and inventory prediction
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── accounts/
│   ├── products/
│   ├── cart/
│   ├── orders/
│   └── dashboard/
│
├── requirements.txt
└── .env.example
```

---

## Application Flow

### Customer

```text
Register / Login
       ↓
Browse Products
       ↓
Select Product
       ↓
Add to Cart
       ↓
Manage Cart
       ↓
Checkout
       ↓
Delivery Location
       ↓
COD / Online Payment
       ↓
Place Order
       ↓
Order Confirmation
       ↓
Order History
```

### Admin

```text
Admin Login
     ↓
Dashboard
     ↓
┌───────────────┬────────────────┬──────────────────┐
│ Products      │ Orders         │ Customers        │
├───────────────┼────────────────┼──────────────────┤
│ Categories    │ Stock          │ Analytics        │
├───────────────┼────────────────┼──────────────────┤
│ Sales Predict │ Inventory Pred │ Reorder Analysis │
└───────────────┴────────────────┴──────────────────┘
```

### Data Science Flow

```text
Historical Orders
       ↓
Data Preparation
       ↓
Feature Engineering
       ↓
Random Forest Model
       ↓
Demand Prediction
       ↓
Inventory Analysis
       ↓
Reorder Recommendation
```

---

## Checkout and Payment

FreshCart provides two delivery-location methods:

### Manual Address

Customers can enter their delivery information manually.

### Map Location

Customers can select their delivery location using the integrated map.

These methods are mutually exclusive: the customer can either enter an address manually or select a location through the map.

The selected delivery information is then used during checkout.

FreshCart also provides:

* Cash on Delivery
* Dummy online payment interface

The online payment flow is intentionally simulated for academic demonstration purposes and does **not** process real financial transactions.

---

## Security and Configuration

Environment-specific configuration is kept outside the committed source code.

The project includes:

```text
.env.example
```

Sensitive configuration such as secret keys and database credentials should be stored in environment variables.

Do not commit a real `.env` file containing credentials or secrets.

---

## Testing

FreshCart contains automated Django tests covering major application components, including:

* Authentication
* Product functionality
* Cart functionality
* Orders and checkout
* Stock management
* Inventory behavior
* Machine-learning prediction functionality

Run the complete test suite with:

```bash
python manage.py test
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Abhishek-M-34/FreshCart.git
cd FreshCart
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on:

```text
.env.example
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create an admin user

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Demo Data

For demonstrating the analytics and machine-learning features, first create the required products and then run:

```bash
python manage.py populate_sales
```

This creates simulated historical order data that can be used by the analytics and prediction modules.

---

## Project Purpose

FreshCart was developed as an academic project to demonstrate the integration of multiple areas of software and data science:

* Full-stack web development
* Django application development
* Database-driven applications
* Authentication and authorization
* E-commerce workflows
* Inventory management
* Business intelligence
* Data visualization
* Data preprocessing
* Feature engineering
* Machine learning
* Demand forecasting
* Inventory prediction

Rather than implementing these technologies as isolated demonstrations, FreshCart integrates them into one practical application.

---

## Future Improvements

The current project provides the core functionality required for the academic demonstration.

Potential future improvements include:

* Real payment gateway integration
* Real-time delivery tracking
* Supplier management
* Automated inventory purchasing
* Cloud deployment
* Advanced demand forecasting models
* More sophisticated recommendation systems
* Customer personalization
* Production-grade monitoring and logging

These are intentionally outside the current academic scope.

---

## Disclaimer

FreshCart is an academic/demo project.

The payment system is simulated and does not process real payments.

Sales and inventory data generated by the population command is simulated data intended for demonstrating analytics and machine-learning functionality.

---

## Author

**Abhishek M**

GitHub:
https://github.com/Abhishek-M-34

Repository:
https://github.com/Abhishek-M-34/FreshCart
