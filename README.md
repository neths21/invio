# AI Inventory Tracker

A sophisticated inventory management system with AI-powered notifications and analysis.

## Features

- Complete inventory management with CRUD operations for products, categories, suppliers
- AI-generated notifications for low stock and irregular inventory activity
- AI analysis of inventory trends and purchase orders
- Automatic reorder suggestions when stock is low
- Machine Learning (ML) analytics for inventory optimization, including:
  - Popularity index calculation
  - Predicted days until reorder
  - AI-generated summaries for inventory insights
- Beautiful and professional user interface
- Authentication system with role-based access

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: NeonDB (PostgreSQL)
- **AI Integration**: Google Gemini 2.0 API
- **Frontend**: Bootstrap 5, Chart.js, DataTables
- **Authentication**: Flask-Login

## Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ai-inventory-tracker.git
   cd ai-inventory-tracker
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   - Create a `.env` file in the project root
   - Add the following variables:
     ```
     FLASK_APP=app
     FLASK_ENV=development
     SECRET_KEY=your_secret_key_here
     DATABASE_URL=postgresql://your_neondb_connection_string_here
     GEMINI_API_KEY=your_gemini_api_key_here
     MAIL_SERVER=smtp.yourmailserver.com
     MAIL_USERNAME=your_email@example.com
     MAIL_PASSWORD=your_email_password
     ```

6. Initialize the database:
   ```
   python -m app.utils.sample_data
   ```

7. Run the application:
   ```
   python run.py
   ```

8. Access the application at http://localhost:5000

## Default Login Credentials

- Admin:
  - Username: admin
  - Password: admin123

- Regular User:
  - Username: user
  - Password: user123

## License

This project is licensed under the MIT License - see the LICENSE file for details.
