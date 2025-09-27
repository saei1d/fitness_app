# Fitness App 🏋️‍♀️

A Django-based fitness management platform.  
This project provides a backend system for managing users, gyms, packages, payments, and user interactions.  

---

## Features
- **Accounts**: user authentication & profile management  
- **Gyms**: manage gym information  
- **Packages**: subscription and membership plans  
- **Finance**: wallet, purchases, and transactions  
- **Interactions**: user favorites and reviews  

---

## Requirements
- Python 3.10+  
- Django 5.x  
- PostgreSQL or SQLite  

---

## Installation

```bash
# Clone the repository
git clone https://github.com/saei1d/fitness_app.git
cd fitness_app

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
