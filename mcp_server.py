from mcp.server.fastmcp import FastMCP
from app import create_app
from models.base import db, SERVER_VERSION
from models.hardware import Device
from models.virtualization import Hypervisor, VirtualMachine
from models.network import VpnTunnel
from models.ipam import IPAddress

mcp = FastMCP("Mini-IPAM-DCIM")
flask_app = create_app()

@mcp.resource("ipam://summary")
def get_summary() -> str:
    with flask_app.app_context():
        return f"Mini IPAM {SERVER_VERSION}: Devices={Device.query.count()}, Hypervisors={Hypervisor.query.count()}, VMs={VirtualMachine.query.count()}, VPNs={VpnTunnel.query.count()}, IPs={IPAddress.query.count()}"

@mcp.tool()
def search_infrastructure(query: str) -> list:
    q = query.lower()
    with flask_app.app_context():
        res = []
        for d in Device.query.all():
            if q in d.hostname.lower(): res.append({"type": "device", "id": d.id, "name": d.hostname, "status": d.status})
        for v in VirtualMachine.query.all():
            if q in v.hostname.lower(): res.append({"type": "vm", "id": v.id, "name": v.hostname, "status": v.status})
        for i in IPAddress.query.all():
            if q in i.ip or q in (i.description or '').lower(): res.append({"type": "ip", "ip": i.ip, "status": i.status, "assigned": i.assigned_label})
        return res

@mcp.tool()
def allocate_free_ip(subnet: str = "", description: str = "") -> dict:
    with flask_app.app_context():
        q = IPAddress.query.filter_by(status='Free')
        if subnet: q = q.filter_by(subnet=subnet)
        ip_obj = q.first()
        if not ip_obj: return {"error": "No free IPs"}
        ip_obj.status = 'Active'
        ip_obj.description = description
        db.session.commit()
        return {"id": ip_obj.id, "ip": ip_obj.ip, "subnet": ip_obj.subnet}

if __name__ == "__main__":
    mcp.run()
