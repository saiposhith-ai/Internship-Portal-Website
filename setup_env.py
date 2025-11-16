#!/usr/bin/env python3
"""
Setup script to generate .env file with secure SECRET_KEY
Run: python setup_env.py
"""

import secrets
import os

def generate_secret_key():
    """Generate a secure random secret key"""
    return secrets.token_hex(32)

def create_env_file():
    """Create .env file with generated SECRET_KEY"""
    
    secret_key = generate_secret_key()
    
    env_content = f"""# Flask Configuration
SECRET_KEY={secret_key}
FLASK_ENV=development

# Database Configuration
# For local development (SQLite)
DATABASE_URL=sqlite:///shramic.db

# For production (PostgreSQL) - uncomment and update
# DATABASE_URL=postgresql://username:password@host:5432/database_name

# Email Configuration (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=shramicnetworks@gmail.com
MAIL_PASSWORD=your-gmail-app-password-here
MAIL_DEFAULT_SENDER=Shramic <shramicnetworks@gmail.com>

# Application Settings
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216
"""
    
    # Check if .env already exists
    if os.path.exists('.env'):
        response = input('⚠️  .env file already exists. Overwrite? (y/N): ')
        if response.lower() != 'y':
            print('❌ Setup cancelled. Keeping existing .env file.')
            return
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print('✅ .env file created successfully!')
    print(f'\n🔑 Your SECRET_KEY: {secret_key}')
    print('\n📝 Next steps:')
    print('1. Update MAIL_PASSWORD with your Gmail App Password')
    print('   - Visit: https://myaccount.google.com/apppasswords')
    print('   - Generate an app password for "Mail"')
    print('2. For production, update DATABASE_URL with PostgreSQL connection')
    print('3. Add .env to .gitignore (already included)')
    print('\n⚠️  NEVER commit .env file to Git!')
    
    # Create .env.example for reference
    env_example = """# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration
DATABASE_URL=sqlite:///shramic.db

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=Your Name <your-email@gmail.com>

# Application Settings
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_example)
    
    print('\n✅ .env.example created (safe to commit to Git)')

if __name__ == '__main__':
    print('🚀 Shramic Platform - Environment Setup')
    print('=' * 50)
    create_env_file()