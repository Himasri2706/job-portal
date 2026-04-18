# Job Portal Completed 🚀

The requested Job Portal Web Application is now fully functional! 

Here are the details of how it was implemented and how to run it.

## Overview

![Job Portal Demo Recording](static/demo.webp)

We built a robust, scalable Python web application utilizing Flask for the backend, and Bootstrap 5 for a modern, responsive user experience. The frontend directly communicates with the database and server via Flask templates.
- **Role-based Authentication:** Separated views and functionality for **Admins**, **Employers**, and **Job Seekers**.
- **Job Handling:** Functionality to add new listings, view listings, filter jobs by category/location, and process applications.
- **Mock API Integration:** An admin tool that safely fetches fake remote properties and injects them seamlessly into the DB.
- **Premium User Interface:** Uses custom styling (`style.css`), modern icons (`Bootstrap Icons`), gradients, blur effects, glassmorphic navigations, hover animations, and a rich dashboard interface.

## How to Run the App

1. **Navigate to the app folder:** Open your terminal and change directories:
   ```cmd
   cd c:\Users\honey\Downloads\job-portal
   ```

2. **Install the dependencies:** Install all the required packages listed in `requirements.txt`:
   ```cmd
   pip install -r requirements.txt
   ```

3. **Start the app:** Run the Python file. The first run automatically sets up the local SQLite database.
   ```cmd
   python app.py
   ```
   > [!TIP]
   > The terminal should log down that the default admin has been created. The default credentials are user: `admin` and password: `admin123`.

4. **Open your browser:** Visit `http://127.0.0.1:5000` to interact with your local platform.

## Validation Results

- Database initializations work automatically as specified in the `init_db()` function in `app.py`.
- Modern styled Bootstrap forms successfully handle registration arrays.
- Clean routing architecture correctly loads Dashboard templates mapping to the appropriate Role (`job_portal\templates`).
