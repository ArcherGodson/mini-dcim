from .base import db

class IPAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), unique=True, nullable=False)
    subnet = db.Column(db.String(45), nullable=False)
    status = db.Column(db.String(20), default='Free')
    description = db.Column(db.String(200))
    interface_id = db.Column(db.Integer, db.ForeignKey('interface.id'), nullable=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    hypervisor_id = db.Column(db.Integer, db.ForeignKey('hypervisor.id'), nullable=True)
    vm_id = db.Column(db.Integer, db.ForeignKey('virtual_machine.id'), nullable=True)
    vpn_id = db.Column(db.Integer, db.ForeignKey('vpn_tunnel.id'), nullable=True)
    vpn = db.relationship('VpnTunnel', backref='ips')

    @property
    def assigned_label(self):
        if self.interface: return f"Порт: {self.interface.owner_name}:{self.interface.name}"
        if self.device: return f"Устройство: {self.device.hostname} ({self.device.device_type})"
        if self.hypervisor: return f"Гипервизор: {self.hypervisor.name}"
        if self.vm: return f"ВМ: {self.vm.hostname}"
        if self.vpn: return f"VPN: {self.vpn.name} ({self.vpn.vpn_type})"
        return ""
