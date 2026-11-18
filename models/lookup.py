from .base import db

class ConfigOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(100), nullable=False)

DEFAULTS = {
    'device_type': ['Server', 'Switch', 'Router', 'Storage', 'Firewall'],
    'status': ['Online', 'Maintenance', 'Offline', 'Decommissioned'],
    'vm_type': ['VM', 'Container', 'vRouter'],
    'hv_type': ['KVM / Proxmox', 'VMware ESXi', 'Hyper-V', 'Docker', 'Kubernetes', 'LXC / Podman', 'Xen'],
    'vpn_type': ['WireGuard', 'OpenVPN', 'IPsec', 'GRE / EoIP', 'VXLAN'],
    'vpn_layer': ['L3', 'L2'],
    'ip_status': ['Free', 'Active', 'Reserved']
}

LABELS = {
    'device_type': 'Типы оборудования',
    'status': 'Статусы объектов',
    'vm_type': 'Типы ВМ / Контейнеров',
    'hv_type': 'Типы гипервизоров',
    'vpn_type': 'Типы VPN',
    'vpn_layer': 'Уровни VPN',
    'ip_status': 'Статусы IP'
}

def seed_options():
    for cat, vals in DEFAULTS.items():
        if ConfigOption.query.filter_by(category=cat).count() == 0:
            for v in vals:
                db.session.add(ConfigOption(category=cat, value=v))
    db.session.commit()

def get_options_map():
    res = {c: [] for c in LABELS}
    for o in ConfigOption.query.order_by(ConfigOption.id).all():
        res.setdefault(o.category, []).append(o)
    return res
