"""Nginx 命令管理：版本查询、语法检查、重载"""
import re
import shutil
import subprocess
from dataclasses import dataclass

import config


@dataclass
class NginxResult:
    success: bool
    message: str
    line_number: int | None = None


def _nginx_available() -> bool:
    return shutil.which(config.NGINX_BIN) is not None


def get_nginx_version() -> str:
    """获取 Nginx 版本号"""
    if not _nginx_available():
        return "未安装（模拟模式）"
    try:
        result = subprocess.run(
            [config.NGINX_BIN, "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stderr + result.stdout
        match = re.search(r"nginx/([\d.]+)", output)
        return match.group(1) if match else output.strip()
    except (subprocess.TimeoutExpired, OSError):
        return "获取失败"


def test_config(conf_path: str | None = None) -> NginxResult:
    """执行 nginx -t 检查配置语法"""
    if not _nginx_available():
        return NginxResult(True, "✅ 配置语法正确（模拟模式，未安装 nginx）")

    cmd = [config.NGINX_BIN, "-t"]
    if conf_path:
        cmd.extend(["-c", conf_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stderr + result.stdout

        if result.returncode == 0:
            return NginxResult(True, "✅ 配置语法正确")

        # 解析错误行号
        line_match = re.search(r":(\d+)", output)
        line_num = int(line_match.group(1)) if line_match else None
        return NginxResult(
            False,
            f"❌ 配置语法错误：{output.strip()}",
            line_number=line_num,
        )
    except subprocess.TimeoutExpired:
        return NginxResult(False, "❌ 检查超时")
    except OSError as e:
        return NginxResult(False, f"❌ 执行失败：{e}")


def reload_nginx() -> NginxResult:
    """重载 Nginx 配置"""
    if not _nginx_available():
        return NginxResult(True, "✅ 已重载（模拟模式，未安装 nginx）")

    test = test_config()
    if not test.success:
        return test

    try:
        result = subprocess.run(
            [config.NGINX_BIN, "-s", "reload"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return NginxResult(True, "✅ Nginx 已重载")
        output = result.stderr + result.stdout
        return NginxResult(False, f"❌ 重载失败：{output.strip()}")
    except subprocess.TimeoutExpired:
        return NginxResult(False, "❌ 重载超时")
    except OSError as e:
        return NginxResult(False, f"❌ 重载失败：{e}")


def get_site_status(site_id: str) -> str:
    """获取站点运行状态（检查配置文件是否存在）"""
    conf_path = config.NGINX_OUTPUT_DIR / f"{site_id}.conf"
    if conf_path.exists():
        return "running"
    return "stopped"
