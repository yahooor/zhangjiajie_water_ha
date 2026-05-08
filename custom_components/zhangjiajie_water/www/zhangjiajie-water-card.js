/**
 * 张家界供水 Lovelace 卡片 v3.1.0
 * 基于 LitElement，无需构建
 * 仅依赖 HA 内置 Lit（2024.1+）
 *
 * 配置:
 *   type: custom:zhangjiajie-water-card
 *   # entity_prefix 可选，自动检测
 */
(() => {
  class ZhangjiajieWaterCard extends HTMLElement {
    static get properties() {
      return {
        hass: { attribute: false },
        config: { attribute: false },
        _loading: { state: true },
      };
    }

    constructor() {
      super();
      this._loading = false;
      this._entityPrefix = null;
      this._shadow = this.attachShadow({ mode: "open" });
    }

    setConfig(config) {
      if (!config) throw new Error("无效的卡片配置");
      this.config = config;
    }

    getCardSize() {
      return 5;
    }

    _getStyles() {
      const isDark = matchMedia("(prefers-color-scheme: dark)").matches
        || document.querySelector("home-assistant")?.shadowRoot?.querySelector("ha-sidebar")?.classList.contains("dark");
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

    _detectPrefix() {
      if (this.config?.entity_prefix) return this.config.entity_prefix;
      if (this._entityPrefix) return this._entityPrefix;
      if (!this.hass?.states) return null;
      for (const id of Object.keys(this.hass.states)) {
        if (id.endsWith("_balance") && id.startsWith("sensor.")) {
          this._entityPrefix = id.replace(/_balance$/, "");
          return this._entityPrefix;
        }
      }
      return null;
    }

    _getEntityId(key) {
      const prefix = this._detectPrefix();
      return prefix ? `${prefix}_${key}` : null;
    }

    _getState(key) {
      const entityId = this._getEntityId(key);
      if (!entityId) return null;
      const entity = this.hass?.states[entityId];
      if (!entity || entity.state === "unavailable" || entity.state === "unknown") return null;
      return entity;
    }

    _getVal(key, fallback = "\u2014") {
      const entity = this._getState(key);
      if (!entity) return fallback;
      const val = entity.state;
      return (val === null || val === undefined || val === "") ? fallback : val;
    }

    _getFriendlyName() {
      const entity = this._getState("balance");
      if (entity?.attributes?.friendly_name) {
        return entity.attributes.friendly_name.replace("\u8d26\u6237\u4f59\u989d", "").trim() || "\u5f20\u5bb6\u754c\u4f9b\u6c34";
      }
      return this.config?.title || "\u5f20\u5bb6\u754c\u4f9b\u6c34";
    }

    _getUpdateTime() {
      const entity = this._getState("balance");
      if (!entity?.last_updated) return "";
      try {
        const dt = new Date(entity.last_updated);
        return `\u66f4\u65b0\u4e8e ${dt.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}`;
      } catch { return ""; }
    }

    async _handleRefresh() {
      if (this._loading) return;
      this._loading = true;
      this._render();
      try {
        const prefix = this._detectPrefix();
        // 精确匹配：从 sensor 前缀推导 button 实体 ID
        const btnId = prefix
          ? `button.${prefix.replace(/^sensor\./, "")}_refresh_data`
          : null;
        if (btnId && this.hass.states[btnId]) {
          await this.hass.callService("button", "press", { entity_id: btnId });
        } else {
          const balanceId = this._getEntityId("balance");
          if (balanceId) {
            await this.hass.callService("homeassistant", "update_entity", { entity_id: balanceId });
          }
        }
        // 智能等待：轮询检查实体更新或超时 10s
        await new Promise(resolve => {
          const start = Date.now();
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
        console.warn("[zjwater-card] \u5237\u65b0\u5931\u8d25:", err);
      } finally {
        this._loading = false;
        this._render();
      }
    }

    _fmt(val, decimals = 2) {
      const n = parseFloat(val);
      return isNaN(n) ? "\u2014" : n.toFixed(decimals);
    }

    connectedCallback() { this._render(); }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }
    get hass() { return this._hass; }

    _render() {
      if (!this._hass || !this.config) {
        this._shadow.innerHTML = `<style>${this._getStyles()}</style><ha-card><div class="error-msg">\u52a0\u8f7d\u4e2d...</div></ha-card>`;
        return;
      }
      const prefix = this._detectPrefix();
      if (!prefix) {
        this._shadow.innerHTML = `<style>${this._getStyles()}</style><ha-card><div class="error-msg">\u672a\u627e\u5230\u5f20\u5bb6\u754c\u4f9b\u6c34\u4f20\u611f\u5668\u5b9e\u4f53\u3002\u8bf7\u786e\u8ba4\u96c6\u6210\u5df2\u914d\u7f6e\uff0c\u6216\u6307\u5b9a entity_prefix\u3002</div></ha-card>`;
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
      const logo = this.config.logo_url || "/local/zhangjiajie_water/logo.png";
      const loading = this._loading ? " loading" : "";

      this._shadow.innerHTML = `<style>${this._getStyles()}</style>
<ha-card>
  <div class="header">
    <img class="header-logo" src="${logo}" alt="logo" onerror="this.style.display='none'">
    <div class="header-info">
      <div class="header-title">${this._getFriendlyName()}</div>
      <div class="header-subtitle">\u5f20\u5bb6\u754c\u5e02\u81ea\u6765\u6c34\u6709\u9650\u8d23\u4efb\u516c\u53f8</div>
    </div>
    <button class="refresh-btn${loading}" title="\u5237\u65b0\u6570\u636e">
      <ha-icon icon="mdi:refresh" style="--mdc-icon-size:20px"></ha-icon>
    </button>
  </div>
  <div class="summary-grid">
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:cash" style="--mdc-icon-size:14px;color:var(--primary-color,#1565c0)"></ha-icon>\u8d26\u6237\u4f59\u989d</div>
      <div class="summary-value highlight">${this._fmt(b)}<span class="summary-unit">\u5143</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:water" style="--mdc-icon-size:14px;color:#1976d2"></ha-icon>\u672c\u671f\u7528\u6c34</div>
      <div class="summary-value">${this._fmt(u, 1)}<span class="summary-unit">m\u00b3</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px;color:#e65100"></ha-icon>\u672c\u671f\u8d39\u7528</div>
      <div class="summary-value">${this._fmt(bill)}<span class="summary-unit">\u5143</span></div>
    </div>
    <div class="summary-item">
      <div class="summary-label"><ha-icon icon="mdi:chart-bar" style="--mdc-icon-size:14px;color:#388e3c"></ha-icon>\u5e74\u7d2f\u8ba1\u7528\u6c34</div>
      <div class="summary-value">${this._fmt(au, 1)}<span class="summary-unit">m\u00b3</span></div>
    </div>
  </div>
  <div class="details-section">
    <div class="details-title"><ha-icon icon="mdi:format-list-bulleted" style="--mdc-icon-size:14px"></ha-icon>\u8d39\u7528\u660e\u7ec6\uff08${rm}\uff09</div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:water-outline" style="--mdc-icon-size:14px"></ha-icon>\u6c34\u8d39</span><span class="detail-value">${this._fmt(wf)} \u5143</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:water-pump" style="--mdc-icon-size:14px"></ha-icon>\u6c61\u6c34\u5904\u7406\u8d39</span><span class="detail-value">${this._fmt(sf)} \u5143</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:14px"></ha-icon>\u5783\u573e\u5904\u7406\u8d39</span><span class="detail-value">${this._fmt(gf)} \u5143</span></div>
    ${parseFloat(of) > 0 ? `<div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:receipt-text-outline" style="--mdc-icon-size:14px"></ha-icon>\u5176\u4ed6\u8d39\u7528</span><span class="detail-value">${this._fmt(of)} \u5143</span></div>` : ""}
  </div>
  <div class="details-section" style="padding-top:0">
    <div class="details-title"><ha-icon icon="mdi:history" style="--mdc-icon-size:14px"></ha-icon>\u4e0a\u6b21\u7f34\u8d39</div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:calendar" style="--mdc-icon-size:14px"></ha-icon>\u7f34\u8d39\u65e5\u671f</span><span class="detail-value">${lpd}</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:cash-100" style="--mdc-icon-size:14px"></ha-icon>\u7f34\u8d39\u91d1\u989d</span><span class="detail-value">${this._fmt(lpa)} \u5143</span></div>
    <div class="detail-row"><span class="detail-label"><ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px"></ha-icon>\u5e74\u7d2f\u8ba1\u6c34\u8d39</span><span class="detail-value">${this._fmt(ab)} \u5143</span></div>
  </div>
  <div class="update-time">${this._getUpdateTime()}</div>
</ha-card>`;

      const btn = this._shadow.querySelector(".refresh-btn");
      if (btn) btn.addEventListener("click", () => this._handleRefresh());
    }
  }

  customElements.define("zhangjiajie-water-card", ZhangjiajieWaterCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "zhangjiajie-water-card",
    name: "\u5f20\u5bb6\u754c\u4f9b\u6c34\u5361\u7247",
    description: "\u663e\u793a\u5f20\u5bb6\u754c\u5e02\u81ea\u6765\u6c34\u8d26\u5355\u3001\u4f59\u989d\u3001\u7528\u6c34\u91cf\u7b49\u4fe1\u606f",
    preview: false,
    documentationURL: "https://github.com/yahooor/zhangjiajie_water_ha",
  });
  console.info("[zjwater-card] v3.1.0 registered (native HTMLElement, no external deps)");
})();
