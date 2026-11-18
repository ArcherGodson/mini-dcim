from datetime import datetime
from .base import db

class MonitorTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    checks = db.Column(db.String(250), nullable=False, default='ICMP')
    interval_ok = db.Column(db.Integer, default=60)
    interval_fail = db.Column(db.Integer, default=10)
    timeout_sec = db.Column(db.Float, default=1.5)

class MonitorSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    default_template_id = db.Column(db.Integer, db.ForeignKey('monitor_template.id'), nullable=True)

class IpMonitorAssign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_id = db.Column(db.Integer, db.ForeignKey('ip_address.id'), unique=True, nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('monitor_template.id'), nullable=False)
    overall_state = db.Column(db.String(20), default='pending')
    last_detail = db.Column(db.String(300), default='Ожидание проверки...')
    updated_at = db.Column(db.DateTime, nullable=True)

    ip_rel = db.relationship('IPAddress', backref=db.backref('mon_assign', uselist=False, cascade='all, delete-orphan'))
    template = db.relationship('MonitorTemplate')

def get_monitor_settings():
    if MonitorTemplate.query.count() == 0:
        t1 = MonitorTemplate(name='Standard-ICMP', checks='ICMP', interval_ok=30, interval_fail=10, timeout_sec=1.5)
        t2 = MonitorTemplate(name='Critical-Web', checks='ICMP, TCP:80, TCP:443', interval_ok=60, interval_fail=5, timeout_sec=1.5)
        t3 = MonitorTemplate(name='Proxmox-Node', checks='ICMP, TCP:22, TCP:8006', interval_ok=45, interval_fail=10, timeout_sec=2.0)
        db.session.add_all([t1, t2, t3])
        db.session.commit()
    s = MonitorSettings.query.first()
    if not s:
        ft = MonitorTemplate.query.first()
        s = MonitorSettings(enabled=False, default_template_id=ft.id if ft else None)
        db.session.add(s)
        db.session.commit()
    return s
