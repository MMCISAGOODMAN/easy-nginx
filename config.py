"""应用配置"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 数据文件
DATA_DIR = BASE_DIR / "data"
SITES_FILE = DATA_DIR / "sites.json"

# 生成的 Nginx 配置输出目录（可通过环境变量覆盖）
# 生产环境可设为 /etc/nginx/sites-enabled
NGINX_OUTPUT_DIR = Path(os.environ.get("NGINX_OUTPUT_DIR", str(BASE_DIR / "nginx_output")))

# 配置备份目录
BACKUP_DIR = BASE_DIR / "backups"

# SSL 证书上传目录
SSL_DIR = BASE_DIR / "ssl_certs"

# Nginx 配置模板
NGINX_TEMPLATE = BASE_DIR / "templates" / "nginx" / "site.conf.j2"

# Flask 配置
SECRET_KEY = os.environ.get("SECRET_KEY", "easy-nginx-local-dev-key")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"

# 是否尝试真实执行 nginx 命令（无 nginx 时自动降级为模拟模式）
NGINX_BIN = os.environ.get("NGINX_BIN", "nginx")
