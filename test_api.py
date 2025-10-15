"""
Simple API testing script
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/api/health")
    print("Health Check:", response.json())

def test_doctor_registration():
    data = {
        "full_name": "Dr. John Smith",
        "mobile_number": "9876543210",
        "email": "john.smith@example.com",
        "password": "password123",
        "specialization": "Orthodontist",
        "years_of_experience": 10,
        "dci_registration_number": "DCI12345",
        "qualification_bds": "BDS from AIIMS",
        "consultation_fee_offline": 500.0,
        "booking_limit_per_day": 15
    }
    
    response = requests.post(f"{BASE_URL}/api/doctors/register", json=data)
    print("\nDoctor Registration:", response.json())
    return response.json()

def test_patient_registration():
    data = {
        "full_name": "Jane Doe",
        "mobile_number": "9876543211",
        "email": "jane.doe@example.com",
        "password": "password123",
        "age": 30,
        "gender": "female",
        "consent_given": True
    }
    
    response = requests.post(f"{BASE_URL}/api/patients/register", json=data)
    print("\nPatient Registration:", response.json())
    return response.json()

def test_lab_registration():
    data = {
        "lab_name": "Perfect Dental Lab",
        "lab_type": "dental",
        "owner_name": "Robert Johnson",
        "mobile_number": "9876543212",
        "email": "contact@perfectdental.com",
        "password": "password123",
        "lab_address": "123 Lab Street",
        "city": "Mumbai",
        "license_number": "LAB12345",
        "services_offered": json.dumps(["Crowns", "Bridges", "Dentures"])
    }
    
    response = requests.post(f"{BASE_URL}/api/labs/register", json=data)
    print("\nLab Registration:", response.json())
    return response.json()

if __name__ == "__main__":
    print("="*50)
    print("Testing Dental Management System API")
    print("="*50)
    
    test_health()
    test_doctor_registration()
    test_patient_registration()
    test_lab_registration()
    
    print("\n" + "="*50)
    print("Tests completed!")
    print("="*50)
