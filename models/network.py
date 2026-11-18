from .base import db

class Vlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))

class VirtualSwitch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vswitch_type = db.Column(db.String(50), default='Linux Bridge')
    hypervisor_id = db.Column(db.Integer, db.ForeignKey('hypervisor.id'), nullable=True)
    vlan_id = db.Column(db.Integer, db.ForeignKey('vlan.id'), nullable=True)
    hypervisor = db.relationship('Hypervisor', backref='vswitches')
    vlan = db.relationship('Vlan', backref='vswitches')

class VpnType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class VpnTunnel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vpn_type = db.Column(db.String(50), default='WireGuard')
    layer = db.Column(db.String(10), default='L3')
    endpoint_a = db.Column(db.String(100))
    endpoint_b = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Online')

class Interface(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    vm_id = db.Column(db.Integer, db.ForeignKey('virtual_machine.id'), nullable=True)
    vswitch_id = db.Column(db.Integer, db.ForeignKey('virtual_switch.id'), nullable=True)
    vlan_id = db.Column(db.Integer, db.ForeignKey('vlan.id'), nullable=True)
    connected_to_id = db.Column(db.Integer, db.ForeignKey('interface.id'), nullable=True)
    ips = db.relationship('IPAddress', backref='interface', lazy=True)
    vswitch = db.relationship('VirtualSwitch', backref='interfaces')
    vlan = db.relationship('Vlan', backref='interfaces')

    @property
    def owner_name(self):
        if self.device: return self.device.hostname
        if self.vm: return f"{self.vm.hostname} (VM)"
        if self.vswitch: return f"vSwitch:{self.vswitch.name}"
        return "Unknown"
