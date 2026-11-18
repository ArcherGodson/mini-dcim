from models.lookup import ConfigOption
import ipaddress
from flask import Blueprint, request, redirect, url_for, jsonify
from models.base import db
from models.geography import Location, Rack
from models.hardware import Device
from models.virtualization import Hypervisor, HypervisorType, VirtualMachine
from models.network import Vlan, VirtualSwitch, VpnTunnel, VpnType, Interface
from models.ipam import IPAddress

crud_bp = Blueprint('crud', __name__)

@crud_bp.route('/options/add', methods=['POST'])
def add_option():
    cat, val = request.form['category'], request.form['value'].strip()
    if val and not ConfigOption.query.filter_by(category=cat, value=val).first():
        db.session.add(ConfigOption(category=cat, value=val))
        db.session.commit()
    return redirect(url_for('dashboard.config'))

@crud_bp.route('/options/edit/<int:opt_id>', methods=['POST'])
def edit_option(opt_id):
    opt = ConfigOption.query.get_or_404(opt_id)
    old_v, new_v = opt.value, request.form['value'].strip()
    if new_v and new_v != old_v:
        opt.value = new_v
        if opt.category == 'device_type': Device.query.filter_by(device_type=old_v).update({'device_type': new_v})
        elif opt.category == 'status':
            for m in (Device, Hypervisor, VirtualMachine, VpnTunnel): m.query.filter_by(status=old_v).update({'status': new_v})
        elif opt.category == 'vm_type': VirtualMachine.query.filter_by(vm_type=old_v).update({'vm_type': new_v})
        elif opt.category == 'hv_type': Hypervisor.query.filter_by(hv_type=old_v).update({'hv_type': new_v})
        elif opt.category == 'vpn_type': VpnTunnel.query.filter_by(vpn_type=old_v).update({'vpn_type': new_v})
        elif opt.category == 'vpn_layer': VpnTunnel.query.filter_by(layer=old_v).update({'layer': new_v})
        elif opt.category == 'ip_status': IPAddress.query.filter_by(status=old_v).update({'status': new_v})
        db.session.commit()
    return redirect(url_for('dashboard.config'))


@crud_bp.route('/add/<string:entity>', methods=['POST'])
def add_entity(entity):
    f = request.form
    if entity == 'location': db.session.add(Location(name=f['name'], address=f.get('address', '')))
    elif entity == 'rack': db.session.add(Rack(name=f['name'], units=int(f['units']), location_id=int(f['location_id'])))
    elif entity == 'device': db.session.add(Device(hostname=f['hostname'], device_type=f['device_type'], u_position=int(f['u_position']), rack_id=int(f['rack_id'])))
    elif entity == 'hv_type':
        if f['name'].strip() and not HypervisorType.query.filter_by(name=f['name'].strip()).first():
            db.session.add(HypervisorType(name=f['name'].strip()))
    elif entity == 'hypervisor':
        t = f['parent_target']
        db.session.add(Hypervisor(name=f['name'], hostname=f['hostname'], hv_type=f['hv_type'], device_id=int(t.split(':')[1]) if t.startswith('dev:') else None, parent_hypervisor_id=int(t.split(':')[1]) if t.startswith('hv:') else None))
    elif entity == 'vm': db.session.add(VirtualMachine(hostname=f['hostname'], vm_type=f['vm_type'], hypervisor_id=int(f['hypervisor_id'])))
    elif entity == 'vlan': db.session.add(Vlan(vid=int(f['vid']), name=f['name'], description=f.get('description', '')))
    elif entity == 'vswitch':
        db.session.add(VirtualSwitch(name=f['name'], vswitch_type=f.get('vswitch_type', 'Linux Bridge'), hypervisor_id=int(f['hypervisor_id']) if f.get('hypervisor_id') else None, vlan_id=int(f['vlan_id']) if f.get('vlan_id') else None))
    elif entity == 'vpn_type':
        if f['name'].strip() and not VpnType.query.filter_by(name=f['name'].strip()).first():
            db.session.add(VpnType(name=f['name'].strip()))
    elif entity == 'vpn':
        db.session.add(VpnTunnel(name=f['name'], vpn_type=f['vpn_type'], layer=f['layer'], endpoint_a=f.get('endpoint_a', ''), endpoint_b=f.get('endpoint_b', '')))
    elif entity == 'interface':
        o = f['owner_target']
        db.session.add(Interface(name=f['name'], device_id=int(o.split(':')[1]) if o.startswith('dev:') else None, vm_id=int(o.split(':')[1]) if o.startswith('vm:') else None, vswitch_id=int(o.split(':')[1]) if o.startswith('vs:') else None, vlan_id=int(f['vlan_id']) if f.get('vlan_id') else None))
    elif entity == 'subnet':
        try:
            net = ipaddress.ip_network(f['cidr'].strip(), strict=False)
            for h in net.hosts():
                if not IPAddress.query.filter_by(ip=str(h)).first(): db.session.add(IPAddress(ip=str(h), subnet=str(net), status='Free'))
        except ValueError: pass
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@crud_bp.route('/connect_ports', methods=['POST'])
def connect_ports():
    p1, p2 = Interface.query.get(int(request.form['port_a'])), Interface.query.get(int(request.form['port_b']))
    if p1 and p2 and p1.id != p2.id:
        p1.connected_to_id, p2.connected_to_id = p2.id, p1.id
        db.session.commit()
    return redirect(url_for('dashboard.config'))

@crud_bp.route('/assign_ip/<int:ip_id>', methods=['POST'])
def assign_ip(ip_id):
    ip_obj = IPAddress.query.get_or_404(ip_id)
    t = request.form.get('target', '')
    ip_obj.interface_id = ip_obj.device_id = ip_obj.hypervisor_id = ip_obj.vm_id = ip_obj.vpn_id = None
    if t.startswith('if:'): ip_obj.interface_id = int(t.split(':')[1])
    elif t.startswith('dev:'): ip_obj.device_id = int(t.split(':')[1])
    elif t.startswith('hv:'): ip_obj.hypervisor_id = int(t.split(':')[1])
    elif t.startswith('vm:'): ip_obj.vm_id = int(t.split(':')[1])
    elif t.startswith('vpn:'): ip_obj.vpn_id = int(t.split(':')[1])
    ip_obj.status = 'Active' if t else 'Free'
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@crud_bp.route('/edit/<string:entity>/<int:item_id>', methods=['POST'])
def edit_entity(entity, item_id):
    f = request.form
    if entity == 'location':
        obj = Location.query.get_or_404(item_id)
        obj.name, obj.address = f['name'], f.get('address', '')
    elif entity == 'rack':
        obj = Rack.query.get_or_404(item_id)
        obj.name, obj.units, obj.location_id = f['name'], int(f['units']), int(f['location_id'])
    elif entity == 'device':
        obj = Device.query.get_or_404(item_id)
        obj.hostname, obj.device_type, obj.u_position, obj.rack_id, obj.status = f['hostname'], f['device_type'], int(f['u_position']), int(f['rack_id']), f['status']
    elif entity == 'hypervisor':
        obj = Hypervisor.query.get_or_404(item_id)
        obj.name, obj.hostname, obj.hv_type, obj.status = f['name'], f['hostname'], f['hv_type'], f['status']
        t = f['parent_target']
        if t.startswith('dev:'): obj.device_id, obj.parent_hypervisor_id = int(t.split(':')[1]), None
        elif t.startswith('hv:') and int(t.split(':')[1]) != obj.id: obj.parent_hypervisor_id, obj.device_id = int(t.split(':')[1]), None
    elif entity == 'vm':
        obj = VirtualMachine.query.get_or_404(item_id)
        obj.hostname, obj.vm_type, obj.hypervisor_id, obj.status = f['hostname'], f['vm_type'], int(f['hypervisor_id']), f['status']
    elif entity == 'vpn':
        obj = VpnTunnel.query.get_or_404(item_id)
        obj.name, obj.vpn_type, obj.layer, obj.endpoint_a, obj.endpoint_b, obj.status = f['name'], f['vpn_type'], f['layer'], f.get('endpoint_a', ''), f.get('endpoint_b', ''), f['status']
    elif entity == 'ip':
        obj = IPAddress.query.get_or_404(item_id)
        obj.ip, obj.subnet, obj.status, obj.description = f['ip'].strip(), f['subnet'].strip(), f['status'], f.get('description', '')
    db.session.commit()
    return redirect(url_for('dashboard.config'))

def collect_cascade_ids(entity, obj):
    removed = [f"{entity}-{obj.id}"]
    if entity == 'location':
        for r in getattr(obj, 'racks', []):
            removed.extend(collect_cascade_ids('rack', r))
    elif entity == 'rack':
        for d in getattr(obj, 'devices', []):
            removed.extend(collect_cascade_ids('device', d))
    elif entity == 'device':
        for i in getattr(obj, 'interfaces', []):
            removed.append(f"interface-{i.id}")
    elif entity == 'hypervisor':
        for v in getattr(obj, 'vms', []):
            removed.extend(collect_cascade_ids('vm', v))
    elif entity == 'vm':
        for i in getattr(obj, 'interfaces', []):
            removed.append(f"interface-{i.id}")
    return removed

@crud_bp.route('/delete/<string:entity>/<int:item_id>', methods=['GET','POST','DELETE'])
def delete_item(entity, item_id):
    model_map = {
        'location': Location,
        'rack': Rack,
        'device': Device,
        'hv_type': HypervisorType,
        'hypervisor': Hypervisor,
        'vm': VirtualMachine,
        'vlan': Vlan,
        'vswitch': VirtualSwitch,
        'vpn_type': VpnType,
        'vpn': VpnTunnel,
        'interface': Interface,
        'ip': IPAddress, 'option': ConfigOption
    }
    m = model_map.get(entity)
    obj = m.query.get(item_id) if m else None
    removed = []
    if obj:
        removed = collect_cascade_ids(entity, obj)
        if entity == 'interface':
            if obj.connected_to_id:
                peer = Interface.query.get(obj.connected_to_id)
                if peer:
                    peer.connected_to_id = None
            for ip in obj.ips:
                ip.interface_id = None
                ip.status = 'Free'
        elif entity in ('device', 'hypervisor', 'vm', 'vpn'):
            for ip in obj.ips:
                ip.device_id = None
                ip.hypervisor_id = None
                ip.vm_id = None
                ip.vpn_id = None
                ip.status = 'Free'
        db.session.delete(obj)
        db.session.commit()
    if request.method == 'DELETE' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"ok": True, "removed": removed})
    return redirect(url_for('dashboard.config'))
