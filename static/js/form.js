/**
 * Easy Nginx - 站点配置表单逻辑
 */
(function () {
    "use strict";

    let currentStep = 1;
    const totalSteps = 4;
    let rules = [];
    let browseCurrentPath = "";

    const MATCH_TYPES = {
        prefix: "以...开头",
        suffix: "以...结尾",
        exact: "完全匹配",
    };

    const ACTIONS = {
        static: "返回静态文件",
        proxy: "转发到后端服务",
        redirect: "重定向到其他地址",
    };

    // DOM elements
    const form = document.getElementById("siteForm");
    const siteId = document.getElementById("siteId").value;
    const rulesList = document.getElementById("rulesList");
    const statusArea = document.getElementById("statusArea");

    // Init
    document.addEventListener("DOMContentLoaded", init);

    function init() {
        rules = Array.isArray(INITIAL_RULES) ? [...INITIAL_RULES] : [];
        renderRules();
        bindEvents();
        validateFields();
    }

    function bindEvents() {
        document.getElementById("nextStepBtn").addEventListener("click", nextStep);
        document.getElementById("prevStepBtn").addEventListener("click", prevStep);
        document.getElementById("addRuleBtn").addEventListener("click", addRule);
        document.getElementById("previewBtn").addEventListener("click", previewConfig);
        document.getElementById("saveBtn").addEventListener("click", saveConfig);
        document.getElementById("reloadBtn").addEventListener("click", reloadNginx);
        document.getElementById("rollbackBtn")?.addEventListener("click", rollbackConfig);
        document.getElementById("browseBtn").addEventListener("click", openBrowse);
        document.getElementById("selectDirBtn").addEventListener("click", selectDirectory);
        document.getElementById("uploadSslBtn").addEventListener("click", uploadSsl);
        document.getElementById("httpsEnabled").addEventListener("change", toggleSsl);

        // Real-time validation
        ["name", "domains", "rootDir"].forEach((id) => {
            const el = document.getElementById(id === "rootDir" ? "rootDir" : id);
            if (el) el.addEventListener("input", validateFields);
        });
        document.getElementById("port").addEventListener("change", validateFields);
    }

    // Step navigation
    function showStep(step) {
        currentStep = step;
        document.querySelectorAll(".form-step").forEach((el) => {
            el.classList.toggle("active", parseInt(el.dataset.step) === step);
        });
        document.querySelectorAll(".step-indicator .step").forEach((el) => {
            const s = parseInt(el.dataset.step);
            el.classList.toggle("active", s === step);
            el.classList.toggle("completed", s < step);
        });

        document.getElementById("prevStepBtn").style.display = step > 1 ? "" : "none";
        document.getElementById("nextStepBtn").style.display = step < totalSteps ? "" : "none";
        if (step === totalSteps) {
            document.getElementById("nextStepBtn").style.display = "none";
        }
    }

    function nextStep() {
        if (!validateCurrentStep()) return;
        if (currentStep < totalSteps) showStep(currentStep + 1);
    }

    function prevStep() {
        if (currentStep > 1) showStep(currentStep - 1);
    }

    function validateCurrentStep() {
        let valid = true;
        if (currentStep === 1) {
            valid = validateName() && validateDomains();
        } else if (currentStep === 2) {
            valid = validateRootDir();
        }
        return valid;
    }

    // Validation
    function validateName() {
        const el = document.getElementById("name");
        const err = document.getElementById("nameError");
        if (!el.value.trim()) {
            err.textContent = "站点名称不能为空";
            return false;
        }
        err.textContent = "";
        return true;
    }

    function validateDomains() {
        const el = document.getElementById("domains");
        const err = document.getElementById("domainsError");
        const val = el.value.trim();
        if (!val) {
            err.textContent = "域名不能为空";
            return false;
        }
        const domains = val.split(",").map((d) => d.trim()).filter(Boolean);
        const pattern = /^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$|^localhost$|^\*$|^(\d{1,3}\.){3}\d{1,3}$/;
        for (const d of domains) {
            if (!pattern.test(d)) {
                err.textContent = `域名格式不正确：${d}`;
                return false;
            }
        }
        err.textContent = "";
        return true;
    }

    function validateRootDir() {
        const el = document.getElementById("rootDir");
        const err = document.getElementById("rootDirError");
        if (!el.value.trim()) {
            err.textContent = "网站根目录不能为空";
            return false;
        }
        err.textContent = "";
        return true;
    }

    function validateFields() {
        validateName();
        validateDomains();
        validateRootDir();
    }

    // Rules management
    function addRule() {
        rules.push({
            trigger_path: "",
            match_type: "prefix",
            action: "static",
            backend_address: "",
            preserve_host: true,
            timeout: 30,
            redirect_target: "",
        });
        renderRules();
    }

    function removeRule(index) {
        rules.splice(index, 1);
        renderRules();
    }

    function moveRule(index, direction) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= rules.length) return;
        [rules[index], rules[newIndex]] = [rules[newIndex], rules[index]];
        renderRules();
    }

    function updateRule(index, field, value) {
        rules[index][field] = value;
        if (field === "action") {
            renderRules();
        }
    }

    function renderRules() {
        if (rules.length === 0) {
            rulesList.innerHTML =
                '<p class="hint" style="padding: 20px; text-align: center;">暂无转发规则。不添加规则时，所有请求将返回网站根目录中的静态文件。</p>';
            return;
        }

        rulesList.innerHTML = rules
            .map((rule, i) => {
                const matchOptions = Object.entries(MATCH_TYPES)
                    .map(
                        ([k, v]) =>
                            `<option value="${k}" ${rule.match_type === k ? "selected" : ""}>${v}</option>`
                    )
                    .join("");

                const actionOptions = Object.entries(ACTIONS)
                    .map(
                        ([k, v]) =>
                            `<option value="${k}" ${rule.action === k ? "selected" : ""}>${v}</option>`
                    )
                    .join("");

                let extraFields = "";
                if (rule.action === "proxy") {
                    extraFields = `
                    <div class="rule-extra-fields">
                        <div class="rule-fields">
                            <div class="form-group">
                                <label>后端地址</label>
                                <input type="text" value="${esc(rule.backend_address)}"
                                    placeholder="例如：127.0.0.1:8080"
                                    onchange="window._updateRule(${i}, 'backend_address', this.value)">
                            </div>
                            <div class="form-group">
                                <label>超时时间（秒）</label>
                                <input type="number" value="${rule.timeout || 30}" min="1"
                                    onchange="window._updateRule(${i}, 'timeout', parseInt(this.value))">
                            </div>
                        </div>
                        <div class="form-group" style="margin-top:12px">
                            <label class="switch-label">
                                <input type="checkbox" ${rule.preserve_host !== false ? "checked" : ""}
                                    onchange="window._updateRule(${i}, 'preserve_host', this.checked)">
                                <span class="switch-slider"></span>
                                保留原始域名
                            </label>
                        </div>
                    </div>`;
                } else if (rule.action === "redirect") {
                    extraFields = `
                    <div class="rule-extra-fields">
                        <div class="form-group">
                            <label>目标地址</label>
                            <input type="text" value="${esc(rule.redirect_target)}"
                                placeholder="例如：https://example.com/new-page"
                                onchange="window._updateRule(${i}, 'redirect_target', this.value)">
                        </div>
                    </div>`;
                }

                return `
                <div class="rule-card">
                    <div class="rule-card-header">
                        <h4>规则 #${i + 1}</h4>
                        <div class="rule-actions">
                            <button type="button" onclick="window._moveRule(${i}, -1)" title="上移" ${i === 0 ? "disabled" : ""}>⬆️</button>
                            <button type="button" onclick="window._moveRule(${i}, 1)" title="下移" ${i === rules.length - 1 ? "disabled" : ""}>⬇️</button>
                            <button type="button" onclick="window._removeRule(${i})" title="删除">🗑️</button>
                        </div>
                    </div>
                    <div class="rule-fields">
                        <div class="form-group">
                            <label>触发路径</label>
                            <input type="text" value="${esc(rule.trigger_path)}"
                                placeholder='例如：/api/ 或 .jpg'
                                onchange="window._updateRule(${i}, 'trigger_path', this.value)">
                        </div>
                        <div class="form-group">
                            <label>匹配方式</label>
                            <select onchange="window._updateRule(${i}, 'match_type', this.value)">${matchOptions}</select>
                        </div>
                        <div class="form-group">
                            <label>处理方式</label>
                            <select onchange="window._updateRule(${i}, 'action', this.value)">${actionOptions}</select>
                        </div>
                    </div>
                    ${extraFields}
                </div>`;
            })
            .join("");
    }

    // Expose rule functions to window for inline handlers
    window._updateRule = updateRule;
    window._removeRule = removeRule;
    window._moveRule = moveRule;

    function esc(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function attr(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
    }

    // Collect form data
    function collectFormData() {
        return {
            name: document.getElementById("name").value.trim(),
            domains: document.getElementById("domains").value.trim(),
            port: parseInt(document.getElementById("port").value),
            https_enabled: document.getElementById("httpsEnabled").checked,
            ssl_cert_path: document.getElementById("sslCertPath").value,
            ssl_key_path: document.getElementById("sslKeyPath").value,
            root_dir: document.getElementById("rootDir").value.trim(),
            index_file: document.getElementById("indexFile").value.trim() || "index.html",
            autoindex: document.getElementById("autoindex").checked,
            rules: rules,
            worker_connections: parseInt(document.getElementById("workerConnections").value) || 1024,
            gzip_enabled: document.getElementById("gzipEnabled").checked,
            cache_duration: document.getElementById("cacheDuration").value,
            ip_whitelist: document.getElementById("ipWhitelist").value,
            custom_config: document.getElementById("customConfig").value,
        };
    }

    function setStatus(message, isSuccess) {
        statusArea.innerHTML = `<span class="${isSuccess ? "success" : "error"}">${message}</span>`;
    }

    // API calls
    async function previewConfig() {
        const data = collectFormData();
        try {
            const res = await fetch(`/api/sites/${siteId}/preview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            if (result.success) {
                document.getElementById("previewContent").textContent = result.config;
                document.getElementById("previewModal").classList.add("show");
            }
        } catch (e) {
            setStatus("❌ 预览失败：" + e.message, false);
        }
    }

    async function saveConfig() {
        if (!validateName() || !validateDomains() || !validateRootDir()) {
            setStatus("❌ 请先填写必填项", false);
            return;
        }
        const data = collectFormData();
        try {
            const res = await fetch(`/api/sites/${siteId}/save`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            setStatus(result.message, result.success);
            if (result.success && siteId === "new" && result.site_id) {
                window.location.href = `/site/${result.site_id}/edit`;
            }
        } catch (e) {
            setStatus("❌ 保存失败：" + e.message, false);
        }
    }

    async function reloadNginx() {
        if (!validateName() || !validateDomains() || !validateRootDir()) {
            setStatus("❌ 请先填写必填项", false);
            return;
        }
        if (!confirm("确定要保存配置并重启 Nginx 吗？")) return;
        const data = collectFormData();
        try {
            const res = await fetch(`/api/sites/${siteId}/reload`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            setStatus(result.message, result.success);
            if (result.success && siteId === "new" && result.site_id) {
                window.location.href = `/site/${result.site_id}/edit`;
            }
        } catch (e) {
            setStatus("❌ 重启失败：" + e.message, false);
        }
    }

    async function rollbackConfig() {
        if (!confirm("确定要回滚到上一个版本吗？")) return;
        try {
            const res = await fetch(`/api/sites/${siteId}/rollback`, { method: "POST" });
            const result = await res.json();
            if (result.success) {
                setStatus(result.message + (result.test_message ? " · " + result.test_message : ""), true);
            } else {
                setStatus("❌ " + (result.errors || [result.message]).join(", "), false);
            }
        } catch (e) {
            setStatus("❌ 回滚失败：" + e.message, false);
        }
    }

    // SSL
    function toggleSsl() {
        const section = document.getElementById("sslUploadSection");
        section.style.display = document.getElementById("httpsEnabled").checked ? "" : "none";
    }

    async function uploadSsl() {
        const cert = document.getElementById("sslCert").files[0];
        const key = document.getElementById("sslKey").files[0];
        if (!cert || !key) {
            alert("请同时选择证书和私钥文件");
            return;
        }
        const formData = new FormData();
        formData.append("cert", cert);
        formData.append("key", key);
        try {
            const res = await fetch(`/api/sites/${siteId}/ssl`, { method: "POST", body: formData });
            const result = await res.json();
            if (result.success) {
                document.getElementById("sslCertPath").value = result.cert_path;
                document.getElementById("sslKeyPath").value = result.key_path;
                document.getElementById("sslStatus").textContent = "✅ 证书已上传";
            } else {
                alert("上传失败：" + (result.errors || []).join("\n"));
            }
        } catch (e) {
            alert("上传失败：" + e.message);
        }
    }

    // Directory browser
    async function openBrowse() {
        browseCurrentPath = document.getElementById("rootDir").value || "/";
        await loadBrowseDir(browseCurrentPath);
        document.getElementById("browseModal").classList.add("show");
    }

    async function loadBrowseDir(path) {
        try {
            const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
            const data = await res.json();
            browseCurrentPath = data.current;
            document.getElementById("browseCurrentPath").textContent = data.current;

            let html = `<div class="browse-item parent" data-path="${attr(data.parent)}">📁 ..</div>`;
            for (const entry of data.entries) {
                html += `<div class="browse-item" data-path="${attr(entry.path)}">📁 ${esc(entry.name)}</div>`;
            }
            if (data.entries.length === 0) {
                html += '<p class="hint" style="padding:12px">此目录下没有子文件夹</p>';
            }
            const list = document.getElementById("browseList");
            list.innerHTML = html;
            list.querySelectorAll(".browse-item[data-path]").forEach((item) => {
                item.addEventListener("click", () => loadBrowseDir(item.dataset.path));
            });
        } catch (e) {
            document.getElementById("browseList").innerHTML =
                '<p class="hint" style="padding:12px;color:red">无法访问此目录</p>';
        }
    }

    function selectDirectory() {
        document.getElementById("rootDir").value = browseCurrentPath;
        closeBrowse();
        validateRootDir();
    }

    // Modal close
    window.closePreview = function () {
        document.getElementById("previewModal").classList.remove("show");
    };

    window.closeBrowse = function () {
        document.getElementById("browseModal").classList.remove("show");
    };

    // Close modal on backdrop click
    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("show");
        });
    });
})();
