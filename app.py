"""Easy Nginx - Nginx 可视化配置工具"""
import json
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

import config
from core import (
    create_site,
    delete_site,
    generate_nginx_config,
    get_latest_backup,
    get_nginx_version,
    get_site,
    get_site_status,
    list_directories,
    load_sites,
    reload_nginx,
    rollback_config,
    save_ssl_cert,
    test_config,
    update_site,
    validate_site_data,
    write_config_file,
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


def _default_site() -> dict:
    return {
        "name": "",
        "domains": "",
        "port": 80,
        "https_enabled": False,
        "ssl_cert_path": "",
        "ssl_key_path": "",
        "root_dir": "",
        "index_file": "index.html",
        "autoindex": False,
        "rules": [],
        "worker_connections": 1024,
        "gzip_enabled": True,
        "cache_duration": "7d",
        "ip_whitelist": "",
        "custom_config": "",
    }


def _parse_form_data(form) -> dict:
    """从表单数据解析站点配置"""
    rules_json = form.get("rules_json", "[]")
    try:
        rules = json.loads(rules_json)
    except json.JSONDecodeError:
        rules = []

    return {
        "name": form.get("name", "").strip(),
        "domains": form.get("domains", "").strip(),
        "port": int(form.get("port", 80)),
        "https_enabled": form.get("https_enabled") == "on",
        "ssl_cert_path": form.get("ssl_cert_path", ""),
        "ssl_key_path": form.get("ssl_key_path", ""),
        "root_dir": form.get("root_dir", "").strip(),
        "index_file": form.get("index_file", "index.html").strip() or "index.html",
        "autoindex": form.get("autoindex") == "on",
        "rules": rules,
        "worker_connections": int(form.get("worker_connections", 1024)),
        "gzip_enabled": form.get("gzip_enabled") == "on",
        "cache_duration": form.get("cache_duration", "7d"),
        "ip_whitelist": form.get("ip_whitelist", ""),
        "custom_config": form.get("custom_config", ""),
    }


@app.context_processor
def inject_globals():
    return {
        "nginx_version": get_nginx_version(),
    }


@app.route("/")
def index():
    sites = load_sites()
    for site in sites:
        site["status"] = get_site_status(site["id"])
    return render_template("index.html", sites=sites)


@app.route("/site/new")
def site_new():
    return render_template("site_form.html", site=_default_site(), is_edit=False)


@app.route("/site/<site_id>/edit")
def site_edit(site_id):
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    return render_template("site_form.html", site=site, is_edit=True)


@app.route("/api/sites", methods=["POST"])
def api_create_site():
    data = request.get_json() or _parse_form_data(request.form)
    errors = validate_site_data(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    site = create_site(data)
    return jsonify({"success": True, "site": site})


@app.route("/api/sites/<site_id>", methods=["PUT"])
def api_update_site(site_id):
    data = request.get_json() or _parse_form_data(request.form)
    errors = validate_site_data(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    site = update_site(site_id, data)
    if not site:
        return jsonify({"success": False, "errors": ["站点不存在"]}), 404
    return jsonify({"success": True, "site": site})


@app.route("/api/sites/<site_id>", methods=["DELETE"])
def api_delete_site(site_id):
    if delete_site(site_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "errors": ["站点不存在"]}), 404


@app.route("/api/sites/<site_id>/preview", methods=["POST"])
def api_preview(site_id):
    data = request.get_json() or _parse_form_data(request.form)
    if site_id != "new":
        existing = get_site(site_id)
        if existing:
            data["id"] = site_id
        else:
            data["id"] = site_id
    else:
        data["id"] = "preview"

    config_text = generate_nginx_config(data)
    return jsonify({"success": True, "config": config_text})


@app.route("/api/sites/<site_id>/save", methods=["POST"])
def api_save(site_id):
    data = request.get_json() or _parse_form_data(request.form)
    errors = validate_site_data(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if site_id == "new":
        site = create_site(data)
        site_id = site["id"]
    else:
        site = update_site(site_id, data)
        if not site:
            return jsonify({"success": False, "errors": ["站点不存在"]}), 404

    config_text = generate_nginx_config(site)
    conf_path = write_config_file(site_id, config_text)
    test_result = test_config()

    return jsonify({
        "success": test_result.success,
        "message": test_result.message,
        "line_number": test_result.line_number,
        "config_path": conf_path,
        "site_id": site_id,
    })


@app.route("/api/sites/<site_id>/reload", methods=["POST"])
def api_reload(site_id):
    data = request.get_json() or _parse_form_data(request.form)
    errors = validate_site_data(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if site_id == "new":
        site = create_site(data)
        site_id = site["id"]
    else:
        site = update_site(site_id, data)
        if not site:
            return jsonify({"success": False, "errors": ["站点不存在"]}), 404

    config_text = generate_nginx_config(site)
    write_config_file(site_id, config_text)

    test_result = test_config()
    if not test_result.success:
        return jsonify({
            "success": False,
            "message": test_result.message,
            "line_number": test_result.line_number,
        })

    reload_result = reload_nginx()
    return jsonify({
        "success": reload_result.success,
        "message": reload_result.message,
        "site_id": site_id,
    })


@app.route("/api/sites/<site_id>/rollback", methods=["POST"])
def api_rollback(site_id):
    if not get_site(site_id):
        return jsonify({"success": False, "errors": ["站点不存在"]}), 404

    has_backup = get_latest_backup(site_id) is not None
    if not has_backup:
        return jsonify({"success": False, "errors": ["没有可回滚的备份"]}), 400

    ok, message = rollback_config(site_id)
    test_result = test_config() if ok else None

    return jsonify({
        "success": ok,
        "message": message,
        "test_message": test_result.message if test_result else None,
    })


@app.route("/api/browse")
def api_browse():
    path = request.args.get("path", str(Path.home()))
    parent = str(Path(path).parent) if Path(path).parent != Path(path) else path
    entries = list_directories(path)
    return jsonify({
        "current": path,
        "parent": parent,
        "entries": entries,
    })


@app.route("/api/sites/<site_id>/ssl", methods=["POST"])
def api_upload_ssl(site_id):
    cert = request.files.get("cert")
    key = request.files.get("key")
    if not cert or not key:
        return jsonify({"success": False, "errors": ["请同时上传证书和私钥"]}), 400

    paths = save_ssl_cert(site_id if site_id != "new" else "temp", cert, key)
    return jsonify({"success": True, **paths})


@app.route("/api/nginx/version")
def api_nginx_version():
    return jsonify({"version": get_nginx_version()})


if __name__ == "__main__":
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.NGINX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
