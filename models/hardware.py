from .base import db

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50))
    u_position = db.Column(db.Integer)
    status = db.Column(db.String(20), default='Online')
    rack_id = db.Column(db.Integer, db.ForeignKey('rack.id'), nullable=False)
    interfaces = db.relationship('Interface', backref='device', cascade="all, delete-orphan", lazy=True)
    hypervisors = db.relationship('Hypervisor', backref='device', lazy=True)
    ips = db.relationship('IPAddress', backref='device', lazy=True)
