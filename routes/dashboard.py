from models.monitoring import MonitorTemplate
from models.monitoring import get_monitor_settings
from routes.monitoring import compute_ip_badge
from models.lookup import get_options_map, LABELS
import os
from flask import Blueprint, render_template, request
from models.base import db, SERVER_VERSION
from models.geography import Location, Rack
from models.hardware import Device
from models.virtualization import Hypervisor, HypervisorType, VirtualMachine
from models.network import Vlan, VirtualSwitch, VpnTunnel, VpnType, Interface
from models.ipam import IPAddress
from models.auth import ApiToken

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    db.session.expire_all()
    st = request.args.get('status', 'Online')
    lid = request.args.get('location_id', '')
    q = request.args.get('q', '').strip().lower()
    devs, hvs, vms, ips, vpns = Device.query.all(), Hypervisor.query.all(), VirtualMachine.query.all(), IPAddress.query.all(), VpnTunnel.query.all()
    if st != 'ALL':
        devs = [d for d in devs if d.status == st]
        hvs = [h for h in hvs if h.status == st]
        vms = [v for v in vms if v.status == st]
        vpns = [v for v in vpns if v.status == st]
        ips = [i for i in ips if i.status == 'Active']
    if lid:
        devs = [d for d in devs if d.rack.location_id == int(lid)]
        hvs = [h for h in hvs if h.get_root_device() and h.get_root_device().rack.location_id == int(lid)]
        vms = [v for v in vms if v.hypervisor.get_root_device() and v.hypervisor.get_root_device().rack.location_id == int(lid)]
    if q:
        devs = [d for d in devs if q in d.hostname.lower() or q in (d.device_type or '').lower()]
        hvs = [h for h in hvs if q in h.name.lower() or q in h.hostname.lower()]
        vms = [v for v in vms if q in v.hostname.lower()]
        ips = [i for i in ips if q in i.ip.lower() or q in (i.description or '').lower() or q in i.assigned_label.lower()]
    return render_template('dashboard.html', version=SERVER_VERSION, mon_settings=get_monitor_settings(), mon_templates=MonitorTemplate.query.all(), ip_badge=compute_ip_badge, opts=get_options_map(), cat_labels=LABELS, locations=Location.query.all(), devices=devs, hvs=hvs, vms=vms, ips=ips, vpns=vpns, vswitches=VirtualSwitch.query.all(), vlans=Vlan.query.all(), interfaces=Interface.query.all(), status_filter=st, loc_filter=lid, q=q)

@dashboard_bp.route('/config')
def config():
    db.session.expire_all()
    auth_enabled = bool(os.environ.get("IPAM_API_TOKEN")) or ApiToken.query.filter_by(is_active=True).count() > 0
    return render_template('config.html', version=SERVER_VERSION, mon_settings=get_monitor_settings(), mon_templates=MonitorTemplate.query.all(), ip_badge=compute_ip_badge, opts=get_options_map(), cat_labels=LABELS, auth_enabled=auth_enabled, tokens=ApiToken.query.all(), locations=Location.query.all(), racks=Rack.query.all(), devices=Device.query.all(), hvs=Hypervisor.query.all(), hv_types=HypervisorType.query.all(), vms=VirtualMachine.query.all(), vswitches=VirtualSwitch.query.all(), vlans=Vlan.query.all(), vpns=VpnTunnel.query.all(), vpn_types=VpnType.query.all(), interfaces=Interface.query.all(), ips=IPAddress.query.all())
