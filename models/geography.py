from .base import db

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    racks = db.relationship('Rack', backref='location', cascade="all, delete-orphan", lazy=True)

class Rack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    units = db.Column(db.Integer, default=42)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    devices = db.relationship('Device', backref='rack', cascade="all, delete-orphan", lazy=True)
