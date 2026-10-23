/**
 * 张家界供水 Lovelace 卡片 v3.2.0
 * 原生 HTMLElement 实现，无外部依赖。
 *
 * 实体发现（v3.2.0 起基于实体注册表，中英文实体名均可识别）：
 *   1. 通过 config/entity_registry/list 找到本集成（platform=zhangjiajie_water）全部实体，
 *      从 unique_id（格式 "{entry_id}_{key}"，entry_id 不含下划线）解析出 key → entity_id 映射；
 *   2. 多账户时可通过 config.entity 指定该账户下任一实体进行绑定；
 *   3. 注册表不可用时回退为旧版 _balance 后缀探测（兼容英文/手工重命名的实体）。
 *
 * 配置:
 *   type: custom:zhangjiajie-water-card
 *   # entity: sensor.xxx   # 多账户时可选，指定该账户任一传感器实体
 */
(() => {
  // 集成全部实体 key（含按钮/二进制传感器），用于从 unique_id 尾段解析
  const ENTITY_KEYS = [
    "balance", "previous_balance", "last_payment_date", "last_payment_time",
    "last_payment_amount", "invoice_code", "customer_code",
    "current_usage", "current_bill", "current_water_fee", "other_fees",
    "sewage_fee", "garbage_fee", "current_month_reading",
    "previous_month_reading", "latest_reading", "latest_reading_month",
    "annual_usage", "annual_bill",
    "low_balance", "refresh_data",
  ];

  class ZhangjiajieWaterCard extends HTMLElement {
    constructor() {
      super();
      this._hass = null;
      this._config = null;
      this._loading = false;
      this._entityMap = null;      // key -> entity_id
      this._mapPromise = null;     // 防止并发初始化
      this._shadow = this.attachShadow({ mode: "open" });
    }

    setConfig(config) {
      if (!config) throw new Error("无效的卡片配置");
      this._config = config;
      this._entityMap = null;
      this._mapPromise = null;
      this._render();
    }

    getCardSize() {
      return 5;
    }

    connectedCallback() {
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._ensureEntityMap();
      this._render();
    }
    get hass() { return this._hass; }

    // ---------- 实体发现 ----------

    async _ensureEntityMap() {
      if (this._entityMap || !this._hass) return;
      if (!this._mapPromise) {
        this._mapPromise = this._initEntityMap()
          .then((map) => {
            this._entityMap = map;
            this._render();
          })
          .catch((err) => {
            console.warn("[zjwater-card] 实体发现失败:", err);
            this._entityMap = {};
            this._render();
          })
          .finally(() => { this._mapPromise = null; });
      }
    }

    async _initEntityMap() {
      try {
        const regs = await this._hass.connection.sendMessagePromise({
          type: "config/entity_registry/list",
        });
        // 按账户（config_entry_id）分组：key -> entity_id
        const groups = new Map();
        for (const reg of regs) {
          if (reg.platform !== "zhangjiajie_water" || !reg.unique_id) continue;
          const sep = reg.unique_id.indexOf("_");
          if (sep <= 0) continue;
          const key = reg.unique_id.slice(sep + 1);
          if (!ENTITY_KEYS.includes(key)) continue;
          const group = groups.get(reg.config_entry_id) || {};
          group[key] = reg.entity_id;
          groups.set(reg.config_entry_id, group);
        }
        let group = null;
        if (this._config.entity) {
          const target = regs.find(
            (r) => r.entity_id === this._config.entity && r.platform === "zhangjiajie_water"
          );
          if (target) group = groups.get(target.config_entry_id);
          else console.warn("[zjwater-card] 配置的 entity 不属于本集成:", this._config.entity);
        }
        if (!group && groups.size >= 1) {
          if (groups.size > 1) {
            console.warn("[zjwater-card] 检测到多个供水账户，默认使用第一个；可在配置中指定 entity 绑定账户");
          }
          group = [...groups.values()][0];
        }
        if (group && group.balance) return group;
      } catch (err) {
        console.warn("[zjwater-card] 实体注册表不可用，回退旧版探测:", err);
      }
      // 回退：旧版 _balance 后缀探测（仅适配英文命名/手工重命名的实体）
      const map = {};
      const prefix = this._legacyDetectPrefix();
      if (prefix) {
        for (const key of ENTITY_KEYS) {
          const id = key === "balance" ? `sensor.${prefix}_balance` : `sensor.${prefix}_${key}`;
          if (this._hass?.states?.[id]) map[key] = id;
        }
        const btn = `button.${prefix}_refresh_data`;
        if (this._hass?.states?.[btn]) map.refresh_data = btn;
      }
      return map;
    }

    _legacyDetectPrefix() {
      if (!this._hass?.states) return null;
      for (const id of Object.keys(this._hass.states)) {
        if (id.startsWith("sensor.") && id.endsWith("_balance")) {
          return id.slice("sensor.".length, -"_balance".length);
        }
      }
      return null;
    }

    // ---------- 数据读取 ----------

    _getState(key) {
      const id = this._entityMap?.[key];
      if (!id) return null;
      const entity = this._hass?.states?.[id];
      if (!entity || entity.state === "unavailable" || entity.state === "unknown") return null;
      return entity;
    }

    _getVal(key, fallback = "—") {
      const entity = this._getState(key);
      if (!entity) return fallback;
      const val = entity.state;
      return (val === null || val === undefined || val === "") ? fallback : val;
    }

    _getFriendlyName() {
      const entity = this._getState("balance");
      if (entity?.attributes?.friendly_name) {
        return entity.attributes.friendly_name.replace("账户余额", "").trim() || "张家界供水";
      }
      return this._config?.title || "张家界供水";
    }

    _getUpdateTime() {
      const entity = this._getState("balance");
      if (!entity?.last_updated) return "";
      try {
        const dt = new Date(entity.last_updated);
        return `更新于 ${dt.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}`;
      } catch { return ""; }
    }

    // ---------- 交互 ----------

    async _handleRefresh() {
      if (this._loading) return;
      this._loading = true;
      this._render();
      const start = Date.now();
      try {
        const btnId = this._entityMap?.refresh_data;
        if (btnId && this._hass.states[btnId]) {
          await this.hass.callService("button", "press", { entity_id: btnId });
        } else if (this._entityMap?.balance) {
          await this.hass.callService("homeassistant", "update_entity", {
            entity_id: this._entityMap.balance,
          });
        }
        // 轮询等待实体更新，最长 10s
        await new Promise((resolve) => {
          const check = () => {
            const entity = this._getState("balance");
            const elapsed = Date.now() - start;
            if ((entity && new Date(entity.last_updated).getTime() > start - 2000) || elapsed > 10000) {
              resolve();
            } else {
              setTimeout(check, 500);
            }
          };
          setTimeout(check, 500);
        });
      } catch (err) {
        console.warn("[zjwater-card] 刷新失败:", err);
      } finally {
        this._loading = false;
        this._render();
      }
    }

    _fmt(val, decimals = 2) {
      const n = parseFloat(val);
      return isNaN(n) ? "—" : n.toFixed(decimals);
    }

    // ---------- 渲染 ----------

    _getStyles() {
      return `
        :host { display: block; }
        ha-card {
          padding: 0;
          overflow: hidden;
          border-radius: 12px;
        }
        .header {
          background: linear-gradient(135deg, var(--primary-color, #1565c0), var(--accent-color, #42a5f5));
          color: #fff;
          padding: 16px 16px 12px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-logo {
          width: 40px; height: 40px;
          border-radius: 8px;
          object-fit: contain;
          background: rgba(255,255,255,0.15);
          padding: 4px;
          flex-shrink: 0;
        }
        .header-info { flex: 1; min-width: 0; }
        .header-title { font-size: 1.05em; font-weight: 600; line-height: 1.2; }
        .header-subtitle {
          font-size: 0.8em; opacity: 0.85; margin-top: 2px;
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .refresh-btn {
          background: rgba(255,255,255,0.2);
          border: none; border-radius: 50%;
          width: 36px; height: 36px;
          cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          color: #fff;
          transition: background 0.2s;
          flex-shrink: 0;
        }
        .refresh-btn:hover { background: rgba(255,255,255,0.35); }
        .refresh-btn.loading { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .summary-grid {
          display: grid; grid-template-columns: 1fr 1fr;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
        }
        .summary-item {
          padding: 14px 16px;
          border-right: 1px solid var(--divider-color, rgba(0,0,0,0.12));
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
        }
        .summary-item:nth-child(2n) { border-right: none; }
        .summary-item:nth-last-child(-n+2) { border-bottom: none; }
        .summary-label {
          font-size: 0.72em;
          color: var(--secondary-text-color, #727272);
          margin-bottom: 4px;
          display: flex; align-items: center; gap: 4px;
        }
        .summary-value {
          font-size: 1.2em; font-weight: 700;
          color: var(--primary-text-color, #212121);
          line-height: 1.1;
        }
        .summary-value.highlight { color: var(--primary-color, #1565c0); }
        .summary-unit {
          font-size: 0.65em; font-weight: 400;
          color: var(--secondary-text-color, #727272);
          margin-left: 2px;
        }
        .details-section { padding: 12px 16px; }
        .details-title {
          font-size: 0.75em; font-weight: 600;
          color: var(--secondary-text-color, #727272);
          letter-spacing: 0.03em; margin-bottom: 8px;
          display: flex; align-items: center; gap: 6px;
        }
        .detail-row {
          display: flex; justify-content: space-between; align-items: center;
          padding: 5px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
          font-size: 0.85em;
        }
        .detail-row:last-child { border-bottom: none; }
        .detail-label {
          color: var(--secondary-text-color, #727272);
          display: flex; align-items: center; gap: 5px;
        }
        .detail-value { color: var(--primary-text-color, #212121); font-weight: 500; }
        .update-time {
          font-size: 0.7em;
          color: var(--secondary-text-color, #727272);
          text-align: right;
          padding: 6px 16px 10px;
        }
        .error-msg {
          padding: 16px;
          color: var(--error-color, #db4437);
        }
      `;
    }

    _render() {
      if (!this._hass || !this._config) {
        this._shadow.innerHTML = `<style>${this._getStyles()}</style><ha-card><div class="error-msg">加载中...</div></ha-card>`;
        return;
      }
      if (!this._entityMap) {
        this._shadow.innerHTML = `<style>${this._getStyles()}</style><ha-card><div class="error-msg">正在检测张家界供水实体...</div></ha-card>`;
        return;
      }
      if (!this._entityMap.balance) {
        this._shadow.innerHTML = `<style>${this._getStyles()}</style><ha-card><div class="error-msg">未找到张家界供水传感器实体。请确认集成已配置并完成首次数据刷新；多账户时可在卡片配置中指定 entity。</div></ha-card>`;
        return;
      }

      const b = this._getVal("balance");
      const u = this._getVal("current_usage");
      const bill = this._getVal("current_bill");
      const au = this._getVal("annual_usage");
      const rm = this._getVal("latest_reading_month");
      const wf = this._getVal("current_water_fee");
      const sf = this._getVal("sewage_fee");
      const gf = this._getVal("garbage_fee");
      const of = this._getVal("other_fees");
      const lpd = this._getVal("last_payment_date");
      const lpa = this._getVal("last_payment_amount");
      const ab = this._getVal("annual_bill");
      const low = this._getState("low_balance");
      const lowChip = low?.state === "on"
        ? `<span style="font-size:0.62em;background:var(--error-color,#db4437);color:#fff;border-radius:4px;padding:1px 6px;margin-left:6px">余额不足</span>`
        : "";
      const logo = this._config.logo_url || "/local/zhangjiajie_water/logo.png";
      const loading = this._loading ? " loading" : "";

      this._shadow.innerHTML = `<style>${this._getStyles()}</style>
<ha-card>
  <div class="header">
    <img class="header-logo" src="${logo}" alt="logo">
    <div class="header-info">
      <div class="header-title">${this._getFriendlyName()}${lowChip}</div>
      <div class="header-subtitle">张家界市自来水有限责任公司</div>
    </div>
    <button class="refresh-btn${loading}" title="刷新数据">
      <ha-icon icon="mdi:refresh" style="--mdc-icon-size:20px"></ha-icon>
    </button>
  </div>
  <div class="summary-grid">
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:cash" style="--mdc-icon-size:14px;color:var(--primary-color,#1565c0)"></ha-icon>账户余额</div>
      <div class="summary-value highlight">${this._fmt(b)}<span class="summary-unit">元</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:water" style="--mdc-icon-size:14px;color:#1976d2"></ha-icon>本期用水</div>
      <div class="summary-value">${this._fmt(u, 1)}<span class="summary-unit">m³</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px;color:#e65100"></ha-icon>本期费用</div>
      <div class="summary-value">${this._fmt(bill)}<span class="summary-unit">元</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:chart-bar" style="--mdc-icon-size:14px;color:#388e3c"></ha-icon>年累计用水</div>
      <div class="summary-value">${this._fmt(au, 1)}<span class="summary-unit">m³</span></div>
    </div>
  </div>
  <div class="details-section">
    <div class="details-title"><ha-icon icon="mdi:format-list-bulleted" style="--mdc-icon-size:14px"></ha-icon>费用明细（${rm}）</div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:water-outline" style="--mdc-icon-size:14px"></ha-icon>水费</span><span class="detail-value">${this._fmt(wf)} 元</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:water-pump" style="--mdc-icon-size:14px"></ha-icon>污水处理费</span><span class="detail-value">${this._fmt(sf)} 元</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:14px"></ha-icon>垃圾处理费</span><span class="detail-value">${this._fmt(gf)} 元</span></div>
    ${parseFloat(of) > 0 ? `<div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:receipt-text-outline" style="--mdc-icon-size:14px"></ha-icon>其他费用</span><span class="detail-value">${this._fmt(of)} 元</span></div>` : ""}
  </div>
  <div class="details-section" style="padding-top:0">
    <div class="details-title"><ha-icon icon="mdi:history" style="--mdc-icon-size:14px"></ha-icon>上次缴费</div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:calendar" style="--mdc-icon-size:14px"></ha-icon>缴费日期</span><span class="detail-value">${lpd}</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:cash-100" style="--mdc-icon-size:14px"></ha-icon>缴费金额</span><span class="detail-value">${this._fmt(lpa)} 元</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px"></ha-icon>年累计水费</span><span class="detail-value">${this._fmt(ab)} 元</span></div>
  </div>
  <div class="update-time">${this._getUpdateTime()}</div>
</ha-card>`;

      const btn = this._shadow.querySelector(".refresh-btn");
      if (btn) btn.addEventListener("click", () => this._handleRefresh());
      const img = this._shadow.querySelector(".header-logo");
      if (img) img.addEventListener("error", () => { img.style.display = "none"; });
    }
  }

  customElements.define("zhangjiajie-water-card", ZhangjiajieWaterCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "zhangjiajie-water-card",
    name: "张家界供水卡片",
    description: "显示张家界市自来水账单、余额、用水量等信息",
    preview: false,
    documentationURL: "https://github.com/yahooor/zhangjiajie_water_ha",
  });
  console.info("[zjwater-card] v3.2.0 registered (entity-registry based detection)");
})();
