"""Nginx 配置生成核心逻辑"""
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from core.validator import parse_domains


def _build_location_block(rule: dict[str, Any]) -> dict[str, Any]:
    """将用户友好的转发规则转换为 Nginx location 配置参数"""
    trigger = rule.get("trigger_path", "").strip()
    match_type = rule.get("match_type", "prefix")
    action = rule.get("action", "static")

    # 构建 location 修饰符
    if match_type == "exact":
        location_modifier = "="
        location_path = trigger
    elif match_type == "suffix":
        location_modifier = "~"
        # 转义正则特殊字符，保留 . 用于扩展名匹配
        escaped = re.escape(trigger).replace(r"\*", ".*")
        location_path = f"{escaped}$"
    else:  # prefix
        location_modifier = ""
        location_path = trigger if trigger.startswith("/") else f"/{trigger}"

    block: dict[str, Any] = {
        "modifier": location_modifier,
        "path": location_path,
        "action": action,
    }

    if action == "proxy":
        backend = rule.get("backend_address", "127.0.0.1:8080").strip()
        if not backend.startswith("http"):
            backend = f"http://{backend}"
        block["proxy_pass"] = backend
        block["preserve_host"] = rule.get("preserve_host", True)
        block["timeout"] = int(rule.get("timeout", 30))

    elif action == "redirect":
        block["redirect_target"] = rule.get("redirect_target", "")

    elif action == "static":
        block["static_path"] = trigger

    return block


def _cache_duration_map() -> dict[str, str | None]:
    return {
        "none": None,
        "1d": "1d",
        "7d": "7d",
        "30d": "30d",
    }


def generate_nginx_config(site: dict[str, Any]) -> str:
    """根据站点配置生成完整的 nginx.conf 片段"""
    template_dir = config.NGINX_TEMPLATE.parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("site.conf.j2")

    domains = parse_domains(site.get("domains", ""))
    rules = site.get("rules", [])
    location_blocks = [_build_location_block(r) for r in rules]

    cache_key = site.get("cache_duration", "7d")
    cache_expires = _cache_duration_map().get(cache_key)

    context = {
        "site_id": site.get("id", "unknown"),
        "site_name": site.get("name", ""),
        "domains": domains,
        "port": int(site.get("port", 80)),
        "https_enabled": site.get("https_enabled", False),
        "ssl_cert_path": site.get("ssl_cert_path", ""),
        "ssl_key_path": site.get("ssl_key_path", ""),
        "root_dir": site.get("root_dir", "/var/www/html"),
        "index_file": site.get("index_file", "index.html"),
        "autoindex": site.get("autoindex", False),
        "rules": location_blocks,
        "worker_connections": int(site.get("worker_connections", 1024)),
        "gzip_enabled": site.get("gzip_enabled", True),
        "cache_expires": cache_expires,
        "ip_whitelist": [
            ip.strip()
            for ip in site.get("ip_whitelist", "").splitlines()
            if ip.strip()
        ],
        "custom_config": site.get("custom_config", "").strip(),
    }

    return template.render(**context)


def get_rule_mapping_table() -> list[dict[str, str]]:
    """返回界面术语与 Nginx 指令的映射表（供文档使用）"""
    return [
        {
            "ui_field": "触发路径 + 以...开头",
            "nginx": "location /path/ { ... }",
            "说明": "前缀匹配，匹配以该路径开头的请求",
        },
        {
            "ui_field": "触发路径 + 以...结尾",
            "nginx": "location ~ \\.jpg$ { ... }",
            "说明": "正则匹配，匹配以该后缀结尾的请求",
        },
        {
            "ui_field": "触发路径 + 完全匹配",
            "nginx": "location = /exact { ... }",
            "说明": "精确匹配，仅匹配完全相同的路径",
        },
        {
            "ui_field": "处理方式：返回静态文件",
            "nginx": "try_files $uri $uri/ =404;",
            "说明": "从网站根目录返回对应文件",
        },
        {
            "ui_field": "处理方式：转发到后端服务",
            "nginx": "proxy_pass http://127.0.0.1:8080;",
            "说明": "将请求转发到指定的后端地址",
        },
        {
            "ui_field": "保留原始域名（开启）",
            "nginx": "proxy_set_header Host $host;",
            "说明": "转发时保留浏览器中的域名",
        },
        {
            "ui_field": "处理方式：重定向到其他地址",
            "nginx": "return 301 https://example.com;",
            "说明": "将访问者跳转到目标地址",
        },
        {
            "ui_field": "允许列出目录（开启）",
            "nginx": "autoindex on;",
            "说明": "无默认页时显示目录文件列表",
        },
        {
            "ui_field": "启用 Gzip 压缩",
            "nginx": "gzip on; gzip_types ...;",
            "说明": "压缩文本类响应以节省带宽",
        },
        {
            "ui_field": "静态文件缓存时间",
            "nginx": "expires 7d; add_header Cache-Control ...;",
            "说明": "设置浏览器缓存静态资源的时长",
        },
        {
            "ui_field": "限制 IP 访问",
            "nginx": "allow 1.2.3.4; deny all;",
            "说明": "仅允许列表中的 IP 访问",
        },
    ]
