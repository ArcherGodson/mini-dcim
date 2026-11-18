from .base import db

class HypervisorType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Hypervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)
    hv_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Online')
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    parent_hypervisor_id = db.Column(db.Integer, db.ForeignKey('hypervisor.id'), nullable=True)
    children = db.relationship('Hypervisor', backref=db.backref('parent_hv', remote_side=[id]), lazy=True)
    vms = db.relationship('VirtualMachine', backref='hypervisor', cascade="all, delete-orphan", lazy=True)
    ips = db.relationship('IPAddress', backref='hypervisor', lazy=True)

    def get_root_device(self):
        curr, seen = self, set()
        while curr and curr.id not in seen:
            seen.add(curr.id)
            if curr.device: return curr.device
            curr = curr.parent_hv
        return None

    def get_chain(self):
        chain, curr, seen = [], self.parent_hv, set()
        while curr and curr.id not in seen:
            seen.add(curr.id)
            chain.append(curr.name)
            if curr.device:
                chain.append(f"{curr.device.hostname} ({curr.device.rack.location.name})")
                break
            curr = curr.parent_hv
        if not chain and self.device:
            chain.append(f"{self.device.hostname} ({self.device.rack.location.name})")
        return " -> ".join(reversed(chain)) if chain else "Без привязки"

class VirtualMachine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    vm_type = db.Column(db.String(50), default='VM')
    status = db.Column(db.String(20), default='Online')
    hypervisor_id = db.Column(db.Integer, db.ForeignKey('hypervisor.id'), nullable=False)
    interfaces = db.relationship('Interface', backref='vm', cascade="all, delete-orphan", lazy=True)
    ips = db.relationship('IPAddress', backref='vm', lazy=True)
