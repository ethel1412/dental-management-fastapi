# Dental Management System - Backend API

Comprehensive dental practice management system with ML-powered X-ray analysis.

## Features

- **Multi-role Authentication**: Doctor, Lab, Patient, Admin
- **Doctor Management**: Profile, specializations, multiple clinics
- **Patient Management**: Registration, clinical profiles, appointments
- **Lab Integration**: Dental & Diagnostic labs with order management
- **Appointment System**: Direct booking with availability checking
- **Clinical Profiles**: Complete 16-section dental case history
- **ML X-ray Analysis**: Automated teeth segmentation using Mask R-CNN
- **Lab Orders**: Direct ordering system with case tracking
- **Payment System**: Dummy payment integration
- **File Management**: Upload certificates, X-rays, STL files, reports

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT
- **ML Framework**: PyTorch
- **File Storage**: Local filesystem

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip

### Setup

1. **Clone the repository**

2. **Create virtual environment**
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

3. **Install dependencies**
pip install -r requirements.txt


4. **Configure environment variables**
Create `.env` file:

DATABASE_URL=postgresql://username:password@localhost:5432/dental_management
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here
UPLOAD_DIR=./uploads
ML_MODEL_PATH=./app/ml_models/maskrcnn_teeth_segmentation.pth


5. **Create database**
createdb dental_management


6. **Setup database tables**
python setup_db.py


7. **Place ML model**
Put your `maskrcnn_teeth_segmentation.pth` file in:
app/ml_models/maskrcnn_teeth_segmentation.pth


## Running the Application
python run.py


The API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/api/docs
- Alternative Docs: http://localhost:8000/api/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/verify-otp` - Verify OTP and get token
- `POST /api/auth/resend-otp` - Resend OTP

### Doctors
- `POST /api/doctors/register` - Register doctor
- `GET /api/doctors/profile` - Get doctor profile
- `PUT /api/doctors/profile` - Update doctor profile
- `GET /api/doctors/search` - Search doctors with filters
- `POST /api/doctors/upload-dci-certificate` - Upload DCI certificate
- `POST /api/doctors/upload-profile-image` - Upload profile image

### Clinics
- `POST /api/clinics/` - Create clinic
- `GET /api/clinics/my-clinics` - Get doctor's clinics
- `PUT /api/clinics/{clinic_id}` - Update clinic
- `POST /api/clinics/{clinic_id}/upload-image` - Upload clinic image

### Labs
- `POST /api/labs/register` - Register lab
- `GET /api/labs/profile` - Get lab profile
- `GET /api/labs/search` - Search labs
- `POST /api/labs/upload-certificate` - Upload registration certificate

### Patients
- `POST /api/patients/register` - Register patient
- `GET /api/patients/profile` - Get patient profile
- `PUT /api/patients/profile` - Update patient profile
- `POST /api/patients/upload-profile-image` - Upload profile image

### Appointments
- `POST /api/appointments/` - Book appointment
- `GET /api/appointments/my-appointments` - Get my appointments
- `GET /api/appointments/{appointment_id}` - Get appointment details
- `PUT /api/appointments/{appointment_id}` - Update appointment
- `DELETE /api/appointments/{appointment_id}` - Cancel appointment
- `GET /api/appointments/doctor/{doctor_id}/availability` - Check availability

### Clinical Profiles
- `POST /api/clinical-profiles/` - Create clinical profile
- `GET /api/clinical-profiles/patient/{patient_id}` - Get patient profiles
- `PUT /api/clinical-profiles/{profile_id}` - Update clinical profile
- `POST /api/clinical-profiles/{profile_id}/upload-xray` - Upload X-ray
- `POST /api/clinical-profiles/{profile_id}/analyze-xray` - Analyze X-ray with ML

### Lab Orders
- `POST /api/lab-orders/` - Create lab order
- `GET /api/lab-orders/my-orders` - Get my orders
- `PUT /api/lab-orders/{order_id}` - Update order status
- `POST /api/lab-orders/{order_id}/upload-stl` - Upload STL file
- `POST /api/lab-orders/{order_id}/upload-result` - Upload result

### Payments
- `POST /api/payments/` - Create payment
- `GET /api/payments/my-payments` - Get payment history
- `GET /api/payments/doctor/earnings` - Get doctor earnings
- `GET /api/payments/lab/earnings` - Get lab earnings

### ML Analysis
- `POST /api/ml-analysis/analyze-xray-direct` - Analyze X-ray directly
- `GET /api/ml-analysis/model-info` - Get ML model info


## Testing
Run the test script:
python test_api.py


## Database Schema

The system includes the following main tables:
- users
- doctors
- clinics
- labs
- patients
- appointments
- clinical_profiles
- lab_orders
- payments

## File Storage Structure
uploads/
├── certificates/ # DCI certificates, licenses
├── xrays/ # X-ray images
├── reports/ # Lab reports, prescriptions
├── stl_files/ # STL files for dental labs
└── profile_images/ # Profile pictures


## ML Model Integration

The system uses a Mask R-CNN model for dental X-ray analysis:
- Model: `maskrcnn_teeth_segmentation.pth`
- Framework: PyTorch
- Purpose: Teeth segmentation and detection
- Output: Detected teeth with bounding boxes and confidence scores

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- OTP verification (displayed on screen for development)

## Development

For development with auto-reload:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


## Production Deployment

1. Set proper environment variables
2. Use production-grade WSGI server (Gunicorn)
3. Set up HTTPS
4. Configure proper CORS origins
5. Use cloud file storage (AWS S3, etc.)
6. Implement proper SMS/Email for OTP

## Future Enhancements

- Real SMS/Email OTP integration
- Payment gateway integration
- Push notifications
- Real-time appointment updates
- Advanced ML analytics
- Telemedicine features

## License

Proprietary - All rights reserved

## Support

For support, contact your development team.
