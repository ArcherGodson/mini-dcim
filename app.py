import os
import argparse
from flask import Flask
from models.base import db
from models.lookup import seed_options
from routes.dashboard import dashboard_bp
from routes.crud import crud_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.monitoring import mon_bp, start_monitor_thread

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('IPAM_DB_URI', 'sqlite:///simple_ipam.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(crud_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(mon_bp)

    with app.app_context():
        db.create_all()
        seed_options()
    start_monitor_thread(app)
    return app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mini IPAM & DCIM Server')
    parser.add_argument('--host', default=os.environ.get('IPAM_HOST', '127.0.0.1'),
                        help='IP-адрес интерфейса для прослушивания (например, 0.0.0.0 для всей сети)')
    parser.add_argument('--port', type=int, default=int(os.environ.get('IPAM_PORT', 5000)),
                        help='TCP-порт сервера (по умолчанию 5000)')
    parser.add_argument('--debug', action='store_true',
                        default=os.environ.get('IPAM_DEBUG', '').lower() in ('1', 'true', 'yes'),
                        help='Запуск в режиме отладки')
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
