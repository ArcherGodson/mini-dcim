import socket, subprocess, platform, threading, time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify, redirect, url_for
from models.base import db
from models.ipam import IPAddress
from models.monitoring import MonitorTemplate, IpMonitorAssign, get_monitor_settings

mon_bp = Blueprint('monitoring', __name__)
_worker_started = False

def log_mon(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MONITOR] {msg}", flush=True)

def check_icmp(ip_str, timeout_sec):
    sys_name = platform.system().lower()
    if sys_name == 'windows':
        cmd = ['ping', '-n', '1', '-w', str(int(timeout_sec * 1000)), ip_str]
    else:
        w = str(int(timeout_sec * 1000)) if sys_name == 'darwin' else str(max(1, int(timeout_sec)))
        cmd = ['ping', '-c', '1', '-W', w, ip_str]
    t0 = time.time()
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_sec + 1)
        ms = int((time.time() - t0) * 1000)
        return ('ok', f'ICMP: OK ({ms}ms)') if res.returncode == 0 else ('fail', 'ICMP: Недоступен')
    except Exception:
        return 'fail', 'ICMP: Таймаут'

def check_tcp(ip_str, port, timeout_sec):
    t0 = time.time()
    try:
        with socket.create_connection((ip_str, int(port)), timeout=timeout_sec):
            ms = int((time.time() - t0) * 1000)
            return 'ok', f'TCP:{port}: OK ({ms}ms)'
    except Exception:
        return 'fail', f'TCP:{port}: Закрыт/Таймаут'

def eval_host(ip_str, checks_str, timeout_sec):
    tokens = [x.strip().upper() for x in (checks_str or '').split(',') if x.strip()] or ['ICMP']
    states, details = [], []
    for tok in tokens:
        if tok == 'ICMP':
            st, det = check_icmp(ip_str, timeout_sec)
            states.append(st); details.append(det)
        elif tok.startswith('TCP:') and tok[4:].strip().isdigit():
            st, det = check_tcp(ip_str, int(tok[4:].strip()), timeout_sec)
            states.append(st); details.append(det)
    if not states:
        return 'pending', 'Нет валидных проверок'
    ok_cnt = sum(1 for s in states if s == 'ok')
    ov = 'green' if ok_cnt == len(states) else ('red' if ok_cnt == 0 else 'orange')
    return ov, ' | '.join(details)

def monitor_loop(app):
    with app.app_context():
        s = get_monitor_settings()
        log_mon(f"Планировщик шаблонов запущен (тик: 1с). Статус: {'ВКЛ' if s.enabled else 'ВЫКЛ'}")
    while True:
        try:
            tasks = []
            with app.app_context():
                db.session.expire_all()
                s = get_monitor_settings()
                if s.enabled:
                    now = datetime.utcnow()
                    if s.default_template_id:
                        created = False
                        for ip_obj in IPAddress.query.filter(IPAddress.status != 'Free').all():
                            if not ip_obj.mon_assign:
                                db.session.add(IpMonitorAssign(ip_id=ip_obj.id, template_id=s.default_template_id, overall_state='pending'))
                                created = True
                        if created:
                            db.session.commit()
                    for a in IpMonitorAssign.query.all():
                        if not a.ip_rel or a.ip_rel.status == 'Free' or not a.template or a.overall_state == 'disabled':
                            continue
                        tpl = a.template
                        wait = max(1, (tpl.interval_ok if a.overall_state == 'green' else tpl.interval_fail) or 10)
                        if a.overall_state == 'pending' or not a.updated_at or a.updated_at + timedelta(seconds=wait) <= now:
                            tasks.append((a.id, a.ip_rel.ip, tpl.name, tpl.checks, tpl.timeout_sec, tpl.interval_ok, tpl.interval_fail))
            if tasks:
                log_mon(f"Тик: список хостов ({len(tasks)} шт.)")
                def run_t(t):
                    aid, ip_s, tn, chks, tout, i_ok, i_fl = t
                    ov, det = eval_host(ip_s, chks, tout)
                    return aid, ip_s, tn, ov, det, i_ok, i_fl
                with ThreadPoolExecutor(max_workers=20) as pool:
                    results = list(pool.map(run_t, tasks))
                with app.app_context():
                    done = datetime.utcnow()
                    for aid, ip_s, tn, ov, det, i_ok, i_fl in results:
                        ao = IpMonitorAssign.query.get(aid)
                        if ao:
                            ao.overall_state, ao.last_detail, ao.updated_at = ov, det, done
                        nxt = i_ok if ov == 'green' else i_fl
                        tag = {'green': '[OK]  ', 'orange': '[WARN]', 'red': '[FAIL]'}.get(ov, '[PEND]')
                        log_mon(f"  {tag} {ip_s:<15} [{tn}] -> {det} (след. через {nxt}с)")
                    db.session.commit()
        except Exception as e:
            log_mon(f"[ERROR] {e}")
        time.sleep(1)

def start_monitor_thread(app):
    global _worker_started
    if not _worker_started:
        _worker_started = True
        threading.Thread(target=monitor_loop, args=(app,), daemon=True).start()

COLOR_MAP = {'green': '#198754', 'orange': '#fd7e14', 'red': '#dc3545', 'pending': '#adb5bd'}

def compute_ip_badge(ip_obj, enabled):
    if not enabled or ip_obj.status == 'Free' or not ip_obj.mon_assign or ip_obj.mon_assign.overall_state == 'disabled':
        return None
    a = ip_obj.mon_assign
    tn = a.template.name if a.template else '?'
    return {'color': COLOR_MAP.get(a.overall_state, '#adb5bd'), 'state': a.overall_state, 'tooltip': f"[{tn}] {a.last_detail}"}

@mon_bp.route('/monitor/settings', methods=['POST'])
def save_monitor_settings():
    s = get_monitor_settings()
    was = s.enabled
    s.enabled = request.form.get('enabled') == 'on'
    did = request.form.get('default_template_id')
    s.default_template_id = int(did) if did else None
    if s.enabled and not was:
        IpMonitorAssign.query.update({'overall_state': 'pending', 'last_detail': 'Проверка запущена...'})
    db.session.commit()
    log_mon(f"Мониторинг: {'ВКЛ' if s.enabled else 'ВЫКЛ'}")
    return redirect(url_for('dashboard.config'))

@mon_bp.route('/monitor/template/add', methods=['POST'])
def add_template():
    nm = request.form['name'].strip()
    if nm and not MonitorTemplate.query.filter_by(name=nm).first():
        db.session.add(MonitorTemplate(
            name=nm, checks=request.form['checks'].strip().upper() or 'ICMP',
            interval_ok=max(1, int(request.form.get('interval_ok', 60))),
            interval_fail=max(1, int(request.form.get('interval_fail', 10))),
            timeout_sec=max(0.3, float(request.form.get('timeout_sec', 1.5)))
        ))
        db.session.commit()
    return redirect(url_for('dashboard.config'))

@mon_bp.route('/monitor/template/edit/<int:tid>', methods=['POST'])
def edit_template(tid):
    t = MonitorTemplate.query.get_or_404(tid)
    t.name = request.form['name'].strip()
    t.checks = request.form['checks'].strip().upper() or 'ICMP'
    t.interval_ok = max(1, int(request.form.get('interval_ok', 60)))
    t.interval_fail = max(1, int(request.form.get('interval_fail', 10)))
    t.timeout_sec = max(0.3, float(request.form.get('timeout_sec', 1.5)))
    IpMonitorAssign.query.filter_by(template_id=tid).update({'overall_state': 'pending'})
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@mon_bp.route('/monitor/template/delete/<int:tid>', methods=['GET', 'POST', 'DELETE'])
def delete_template(tid):
    t = MonitorTemplate.query.get_or_404(tid)
    IpMonitorAssign.query.filter_by(template_id=tid).delete()
    db.session.delete(t)
    db.session.commit()
    if request.method == 'DELETE' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'removed': [f'montpl-{tid}']})
    return redirect(url_for('dashboard.config'))

@mon_bp.route('/monitor/assign', methods=['POST'])
def assign_template():
    ip_id = int(request.form['ip_id'])
    tid = request.form.get('template_id')
    ex = IpMonitorAssign.query.filter_by(ip_id=ip_id).first()
    if not tid:
        if ex:
            ex.overall_state = 'disabled'
            ex.last_detail = 'Мониторинг отключён'
        else:
            fallback_tid = get_monitor_settings().default_template_id or (MonitorTemplate.query.first().id if MonitorTemplate.query.first() else None)
            if fallback_tid:
                db.session.add(IpMonitorAssign(ip_id=ip_id, template_id=fallback_tid, overall_state='disabled', last_detail='Мониторинг отключён'))
    else:
        if ex:
            ex.template_id, ex.overall_state, ex.last_detail = int(tid), 'pending', 'Смена шаблона...'
        else:
            db.session.add(IpMonitorAssign(ip_id=ip_id, template_id=int(tid), overall_state='pending'))
    db.session.commit()
    return redirect(url_for('dashboard.config'))

@mon_bp.route('/api/v1/monitor/statuses', methods=['GET'])
def api_monitor_statuses():
    db.session.expire_all()
    s = get_monitor_settings()
    data, assigns = {}, {}
    if s.enabled:
        for ip_obj in IPAddress.query.filter(IPAddress.status != 'Free').all():
            b = compute_ip_badge(ip_obj, True)
            if b: data[str(ip_obj.id)] = b
            if ip_obj.mon_assign:
                a = ip_obj.mon_assign
                assigns[str(a.id)] = {'state': a.overall_state, 'color': COLOR_MAP.get(a.overall_state, '#adb5bd'), 'detail': a.last_detail}
    return jsonify({'enabled': s.enabled, 'statuses': data, 'assigns': assigns})
