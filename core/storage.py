"""站点数据存储与备份管理"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import config


def _ensure_dirs() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    config.NGINX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.SSL_DIR.mkdir(parents=True, exist_ok=True)


def load_sites() -> list[dict[str, Any]]:
    _ensure_dirs()
    if not config.SITES_FILE.exists():
        return []
    with open(config.SITES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_sites(sites: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    with open(config.SITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False, indent=2)


def get_site(site_id: str) -> dict[str, Any] | None:
    for site in load_sites():
        if site.get("id") == site_id:
            return site
    return None


def create_site(data: dict[str, Any]) -> dict[str, Any]:
    sites = load_sites()
    site = {"id": str(uuid4()), **data}
    sites.append(site)
    save_sites(sites)
    return site


def update_site(site_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    sites = load_sites()
    for i, site in enumerate(sites):
        if site.get("id") == site_id:
            updated = {**site, **data, "id": site_id}
            sites[i] = updated
            save_sites(sites)
            return updated
    return None


def delete_site(site_id: str) -> bool:
    sites = load_sites()
    new_sites = [s for s in sites if s.get("id") != site_id]
    if len(new_sites) == len(sites):
        return False
    save_sites(new_sites)
    # 删除对应的配置文件
    conf_path = config.NGINX_OUTPUT_DIR / f"{site_id}.conf"
    if conf_path.exists():
        conf_path.unlink()
    return True


def backup_config(site_id: str, content: str) -> str:
    """备份旧配置，返回备份文件路径"""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config.BACKUP_DIR / f"{site_id}_{timestamp}.conf"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(backup_path)


def get_latest_backup(site_id: str) -> Path | None:
    """获取该站点最新的备份文件"""
    _ensure_dirs()
    backups = sorted(
        config.BACKUP_DIR.glob(f"{site_id}_*.conf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups[0] if backups else None


def rollback_config(site_id: str) -> tuple[bool, str]:
    """回滚到上一个备份版本"""
    backup = get_latest_backup(site_id)
    if not backup:
        return False, "没有可回滚的备份"

    conf_path = config.NGINX_OUTPUT_DIR / f"{site_id}.conf"
    content = backup.read_text(encoding="utf-8")
    conf_path.write_text(content, encoding="utf-8")

    # 删除已使用的备份
    backup.unlink()
    return True, f"已回滚到备份：{backup.name}"


def write_config_file(site_id: str, content: str) -> str:
    """写入配置文件，自动备份旧版本"""
    _ensure_dirs()
    conf_path = config.NGINX_OUTPUT_DIR / f"{site_id}.conf"
    if conf_path.exists():
        backup_config(site_id, conf_path.read_text(encoding="utf-8"))
    conf_path.write_text(content, encoding="utf-8")
    return str(conf_path)


def list_directories(path: str) -> list[dict[str, str]]:
    """列出目录内容，用于路径浏览"""
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            return []
        entries = []
        for item in sorted(target.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                entries.append({"name": item.name, "path": str(item)})
        return entries
    except (OSError, PermissionError):
        return []


def save_ssl_cert(site_id: str, cert_file, key_file) -> dict[str, str]:
    """保存 SSL 证书文件"""
    _ensure_dirs()
    site_ssl_dir = config.SSL_DIR / site_id
    site_ssl_dir.mkdir(parents=True, exist_ok=True)

    cert_path = site_ssl_dir / "cert.pem"
    key_path = site_ssl_dir / "key.pem"

    cert_file.save(cert_path)
    key_file.save(key_path)

    return {"cert_path": str(cert_path), "key_path": str(key_path)}
