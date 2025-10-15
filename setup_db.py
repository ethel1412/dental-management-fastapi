"""
Database setup script
Run this to create the database and tables
"""
from app.database import engine, Base
from app.models import *
from app.services.file_service import FileService

def setup_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
    
    print("\nCreating upload directories...")
    FileService.ensure_upload_dirs()
    print("✓ Upload directories created successfully")
    
    print("\n" + "="*50)
    print("Database setup completed!")
    print("="*50)
    print("\nYou can now run the application:")
    print("  python run.py")
    print("\nAPI Documentation will be available at:")
    print("  http://localhost:8000/api/docs")
    print("="*50)

if __name__ == "__main__":
    setup_database()
