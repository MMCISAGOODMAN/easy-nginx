"""表单与站点数据校验"""
import re
from typing import Any


DOMAIN_PATTERN = re.compile(
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    r"|^localhost$"
    r"|^\*$"
    r"|^([0-9]{1,3}\.){3}[0-9]{1,3}$"
)

IP_CIDR_PATTERN = re.compile(
    r"^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$"
)


def validate_domains(domains_str: str) -> tuple[bool, str]:
    if not domains_str or not domains_str.strip():
        return False, "域名不能为空"
    domains = [d.strip() for d in domains_str.split(",") if d.strip()]
    if not domains:
        return False, "请至少填写一个域名"
    for domain in domains:
        if not DOMAIN_PATTERN.match(domain):
            return False, f"域名格式不正确：{domain}"
    return True, ""


def validate_port(port: Any) -> tuple[bool, str]:
    try:
        port_num = int(port)
    except (TypeError, ValueError):
        return False, "端口号必须是数字"
    if port_num not in (80, 81, 82, 8080, 443):
        return False, "端口号不在允许范围内"
    return True, ""


def validate_site_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "站点名称不能为空"
    if len(name.strip()) > 50:
        return False, "站点名称不能超过50个字符"
    return True, ""


def validate_rule(rule: dict[str, Any], index: int) -> list[str]:
    errors = []
    prefix = f"转发规则第{index + 1}条"

    trigger = rule.get("trigger_path", "").strip()
    if not trigger:
        errors.append(f"{prefix}：触发路径不能为空")

    match_type = rule.get("match_type")
    if match_type not in ("prefix", "suffix", "exact"):
        errors.append(f"{prefix}：匹配方式无效")

    action = rule.get("action")
    if action not in ("static", "proxy", "redirect"):
        errors.append(f"{prefix}：处理方式无效")

    if action == "proxy":
        backend = rule.get("backend_address", "").strip()
        if not backend:
            errors.append(f"{prefix}：后端地址不能为空")
        timeout = rule.get("timeout", 30)
        try:
            if int(timeout) <= 0:
                errors.append(f"{prefix}：超时时间必须大于0")
        except (TypeError, ValueError):
            errors.append(f"{prefix}：超时时间必须是数字")

    if action == "redirect":
        target = rule.get("redirect_target", "").strip()
        if not target:
            errors.append(f"{prefix}：重定向目标地址不能为空")

    return errors


def validate_site_data(data: dict[str, Any]) -> list[str]:
    errors = []

    ok, msg = validate_site_name(data.get("name", ""))
    if not ok:
        errors.append(msg)

    ok, msg = validate_domains(data.get("domains", ""))
    if not ok:
        errors.append(msg)

    ok, msg = validate_port(data.get("port", 80))
    if not ok:
        errors.append(msg)

    if data.get("https_enabled") and not data.get("ssl_cert_path"):
        errors.append("启用 HTTPS 时需要上传证书")

    root_dir = data.get("root_dir", "").strip()
    if not root_dir:
        errors.append("网站根目录不能为空")

    for i, rule in enumerate(data.get("rules", [])):
        errors.extend(validate_rule(rule, i))

    ip_list = data.get("ip_whitelist", "").strip()
    if ip_list:
        for line in ip_list.splitlines():
            line = line.strip()
            if line and not IP_CIDR_PATTERN.match(line):
                errors.append(f"IP 格式不正确：{line}")

    return errors


def parse_domains(domains_str: str) -> list[str]:
    return [d.strip() for d in domains_str.split(",") if d.strip()]
