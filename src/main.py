import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.reports import reports_bp
from src.routes.anomalies import anomalies_bp
from src.routes.email_service import email_bp

from src.routes.dashboard import dashboard_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(reports_bp, url_prefix='/api')
app.register_blueprint(anomalies_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(email_bp, url_prefix='/api')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Initialize default users if they don't exist
    from src.models.user import User
    
    default_users = [
        {'staff_number': '85891', 'role': 'Meter Reader'},
        {'staff_number': '80909', 'role': 'Meter Reader'},  # Omweri
        {'staff_number': '86002', 'role': 'Meter Reader'},  # Samwel
        {'staff_number': '53050', 'role': 'Meter Reader'},  # Mackenzie
        {'staff_number': '85915', 'role': 'Back Office'},   # Moenga
        {'staff_number': '84184', 'role': 'Meter Reader'},  # Sudi
        {'staff_number': '12345', 'role': 'Supervisor'},    # Sample supervisor
        {'staff_number': '67890', 'role': 'Commercial Engineer'}  # Sample commercial engineer
    ]
    
    for user_data in default_users:
        existing_user = User.query.filter_by(staff_number=user_data['staff_number']).first()
        if not existing_user:
            user = User(
                staff_number=user_data['staff_number'],
                role=user_data['role']
            )
            # Set PIN as first 4 digits of staff number
            pin = user_data['staff_number'][:4]
            user.set_pin(pin)
            
            # Set default security question and answer
            user.security_question = "What is your staff number?"
            user.set_security_answer(user_data['staff_number'])
            
            db.session.add(user)
    
    db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

