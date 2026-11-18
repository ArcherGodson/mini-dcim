from flask import Blueprint, request, jsonify
from models.base import db, SERVER_VERSION, SCHEMA_VERSION
from models.geography import Location, Rack
from models.hardware import Device
from models.virtualization import Hypervisor, VirtualMachine
from models.network import Vlan, VirtualSwitch, VpnTunnel, Interface
from models.ipam import IPAddress
from routes.auth import optional_token_required

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/health', methods=['GET'])
@optional_token_required
def health():
    return jsonify({"status": "ok", "version": SERVER_VERSION, "schema_version": SCHEMA_VERSION})

@api_bp.route('/inventory', methods=['GET'])
@optional_token_required
def inventory():
    st = request.args.get('status')
    devs = Device.query.filter_by(status=st).all() if st else Device.query.all()
    vms = VirtualMachine.query.filter_by(status=st).all() if st else VirtualMachine.query.all()
    return jsonify({
        "locations": [{"id": l.id, "name": l.name, "address": l.address} for l in Location.query.all()],
        "racks": [{"id": r.id, "name": r.name, "units": r.units, "location_id": r.location_id} for r in Rack.query.all()],
        "devices": [{"id": d.id, "hostname": d.hostname, "type": d.device_type, "u": d.u_position, "status": d.status, "rack_id": d.rack_id} for d in devs],
        "hypervisors": [{"id": h.id, "name": h.name, "hostname": h.hostname, "type": h.hv_type, "status": h.status} for h in Hypervisor.query.all()],
        "vms": [{"id": v.id, "hostname": v.hostname, "type": v.vm_type, "status": v.status, "hypervisor_id": v.hypervisor_id} for v in vms],
        "vpns": [{"id": v.id, "name": v.name, "type": v.vpn_type, "layer": v.layer, "status": v.status} for v in VpnTunnel.query.all()],
        "ips": [{"id": i.id, "ip": i.ip, "subnet": i.subnet, "status": i.status, "assigned": i.assigned_label} for i in IPAddress.query.all()]
    })

@api_bp.route('/ips/allocate', methods=['POST'])
@optional_token_required
def allocate_ip():
    data = request.get_json(force=True)
    q = IPAddress.query.filter_by(status='Free')
    if data.get('subnet'): q = q.filter_by(subnet=data['subnet'])
    ip_obj = q.first()
    if not ip_obj: return jsonify({"error": "No free IP available"}), 404
    ip_obj.status = 'Active'
    ip_obj.description = data.get('description', '')
    if data.get('device_id'): ip_obj.device_id = data['device_id']
    elif data.get('hypervisor_id'): ip_obj.hypervisor_id = data['hypervisor_id']
    elif data.get('vm_id'): ip_obj.vm_id = data['vm_id']
    elif data.get('vpn_id'): ip_obj.vpn_id = data['vpn_id']
    db.session.commit()
    return jsonify({"id": ip_obj.id, "ip": ip_obj.ip, "status": ip_obj.status, "assigned": ip_obj.assigned_label})
