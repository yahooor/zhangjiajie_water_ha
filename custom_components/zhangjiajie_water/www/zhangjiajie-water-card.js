/**
 * 张家界供水 Lovelace 卡片
 * 基于 LitElement，无需构建
 * version: 3.0.1
 *
 * 配置示例:
 *   type: custom:zhangjiajie-water-card
 *   # entity_prefix 可选，不填则自动检测
 *   # entity_prefix: sensor.zhang_jia_jie_gong_shui_xxxx
 */
(() => {
  // Lit 兼容层：优先从 HA 内置加载，fallback 到 unpkg CDN
  let LitElement, html, css;
  try {
    // HA 2024.11+ 内置 Lit
    const lit = window.require?.("lit") || {};
    LitElement = lit.LitElement;
    html = lit.html;
    css = lit.css;
  } catch (e) { /* ignore */ }

  if (!LitElement) {
    // 动态 import 兼容层（将在 load() 中处理）
    console.info("[zjwater-card] 尝试加载 Lit 依赖...");
  }

  class ZhangjiajieWaterCard extends (LitElement || HTMLElement) {
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
    }

    setConfig(config) {
      // entity_prefix 可选，不填则自动检测
      this.config = config;
    }

    static get styles() {
      if (typeof css === "undefined") return undefined;
      return css`
        :host {
          display: block;
        }
        ha-card {
          padding: 0;
          overflow: hidden;
          border-radius: 12px;
        }
        .header {
          background: linear-gradient(135deg, #1565c0, #42a5f5);
          color: #fff;
          padding: 16px 16px 12px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-logo {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          object-fit: contain;
          background: rgba(255,255,255,0.15);
          padding: 4px;
          flex-shrink: 0;
        }
        .header-info {
          flex: 1;
          min-width: 0;
        }
        .header-title {
          font-size: 1.05em;
          font-weight: 600;
          line-height: 1.2;
        }
        .header-subtitle {
          font-size: 0.8em;
          opacity: 0.85;
          margin-top: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .refresh-btn {
          background: rgba(255,255,255,0.2);
          border: none;
          border-radius: 50%;
          width: 36px;
          height: 36px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          transition: background 0.2s, transform 0.3s;
          flex-shrink: 0;
        }
        .refresh-btn:hover {
          background: rgba(255,255,255,0.35);
        }
        .refresh-btn.loading {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .summary-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
        }
        .summary-item {
          padding: 14px 16px;
          border-right: 1px solid var(--divider-color, rgba(0,0,0,0.12));
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
        }
        .summary-item:nth-child(2n) {
          border-right: none;
        }
        .summary-item:nth-last-child(-n+2) {
          border-bottom: none;
        }
        .summary-label {
          font-size: 0.72em;
          color: var(--secondary-text-color, #727272);
          margin-bottom: 4px;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .summary-value {
          font-size: 1.2em;
          font-weight: 700;
          color: var(--primary-text-color, #212121);
          line-height: 1.1;
        }
        .summary-value.highlight {
          color: #1565c0;
        }
        .summary-unit {
          font-size: 0.65em;
          font-weight: 400;
          color: var(--secondary-text-color, #727272);
          margin-left: 2px;
        }
        .details-section {
          padding: 12px 16px;
        }
        .details-title {
          font-size: 0.75em;
          font-weight: 600;
          color: var(--secondary-text-color, #727272);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .detail-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 5px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
          font-size: 0.85em;
        }
        .detail-row:last-child {
          border-bottom: none;
        }
        .detail-label {
          color: var(--secondary-text-color, #727272);
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .detail-value {
          color: var(--primary-text-color, #212121);
          font-weight: 500;
        }
        .update-time {
          font-size: 0.7em;
          color: var(--secondary-text-color, #727272);
          text-align: right;
          padding: 6px 16px 10px;
        }
      `;
    }

    /**
     * 自动检测实体前缀（扫描 hass.states 中匹配 balance 传感器的实体）
     */
    _detectPrefix() {
      if (this.config?.entity_prefix) return this.config.entity_prefix;
      if (this._entityPrefix) return this._entityPrefix;
      if (!this.hass?.states) return null;

      // 查找 sensor.*_balance 类型的实体（本集成特征）
      for (const [id, state] of Object.entries(this.hass.states)) {
        if (id.endsWith("_balance") && id.startsWith("sensor.")) {
          this._entityPrefix = id.replace(/_balance$/, "");
          return this._entityPrefix;
        }
      }
      return null;
    }

    _getEntityId(key) {
      const prefix = this._detectPrefix();
      if (!prefix) return null;
      return `${prefix}_${key}`;
    }

    _getState(key) {
      const entityId = this._getEntityId(key);
      if (!entityId) return null;
      const entity = this.hass?.states[entityId];
      if (!entity || entity.state === "unavailable" || entity.state === "unknown") {
        return null;
      }
      return entity;
    }

    _getVal(key, fallback = "—") {
      const entity = this._getState(key);
      if (!entity) return fallback;
      const val = entity.state;
      if (val === null || val === undefined || val === "") return fallback;
      return val;
    }

    _getFriendlyName() {
      const entity = this._getState("balance");
      if (entity?.attributes?.friendly_name) {
        return entity.attributes.friendly_name.replace("账户余额", "").trim() || "张家界供水";
      }
      return this.config?.title || "张家界供水";
    }

    _getUpdateTime() {
      const entity = this._getState("balance");
      if (!entity?.last_updated) return "";
      try {
        const dt = new Date(entity.last_updated);
        return `更新于 ${dt.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}`;
      } catch {
        return "";
      }
    }

    async _handleRefresh(e) {
      e.stopPropagation();
      if (this._loading) return;
      this._loading = true;
      try {
        // 查找刷新按钮实体（button.*_refresh_data）
        const btnEntity = Object.keys(this.hass.states).find(
          id => id.startsWith("button.") && id.endsWith("_refresh_data")
        );
        if (btnEntity) {
          await this.hass.callService("button", "press", { entity_id: btnEntity });
        } else {
          // 回退：触发实体更新
          const balanceId = this._getEntityId("balance");
          if (balanceId) {
            await this.hass.callService("homeassistant", "update_entity", { entity_id: balanceId });
          }
        }
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (err) {
        console.warn("[zjwater-card] 刷新失败:", err);
      } finally {
        this._loading = false;
      }
    }

    _fmt(val, decimals = 2) {
      const n = parseFloat(val);
      if (isNaN(n)) return "—";
      return n.toFixed(decimals);
    }

    render() {
      if (!this.hass || !this.config) return html`<ha-card><div style="padding:16px">加载中...</div></ha-card>`;

      // 自动检测前缀
      const prefix = this._detectPrefix();
      if (!prefix) {
        return html`<ha-card><div style="padding:16px;color:var(--error-color)">未找到张家界供水传感器实体。请确认集成已正确配置，或在卡片中指定 entity_prefix。</div></ha-card>`;
      }

      const balance = this._getVal("balance");
      const usage = this._getVal("current_usage");
      const bill = this._getVal("current_bill");
      const annualUsage = this._getVal("annual_usage");
      const readingMonth = this._getVal("latest_reading_month");
      const waterFee = this._getVal("current_water_fee");
      const sewageFee = this._getVal("sewage_fee");
      const garbageFee = this._getVal("garbage_fee");
      const otherFees = this._getVal("other_fees");
      const lastPayDate = this._getVal("last_payment_date");
      const lastPayAmt = this._getVal("last_payment_amount");
      const annualBill = this._getVal("annual_bill");
      const logoUrl = this.config.logo_url || "/local/zhangjiajie_water/logo.png";

      return html`
        <ha-card>
          <div class="header">
            <img class="header-logo" src="${logoUrl}" alt="logo" @error=${e => e.target.style.display='none'}>
            <div class="header-info">
              <div class="header-title">${this._getFriendlyName()}</div>
              <div class="header-subtitle">张家界市自来水有限责任公司</div>
            </div>
            <button class="refresh-btn ${this._loading ? 'loading' : ''}" @click=${this._handleRefresh} title="刷新数据">
              <ha-icon icon="mdi:refresh" style="--mdc-icon-size:20px"></ha-icon>
            </button>
          </div>

          <div class="summary-grid">
            <div class="summary-item">
              <div class="summary-label">
                <ha-icon icon="mdi:cash" style="--mdc-icon-size:14px;color:#1565c0"></ha-icon>账户余额
              </div>
              <div class="summary-value highlight">
                ${this._fmt(balance)}<span class="summary-unit">元</span>
              </div>
            </div>
            <div class="summary-item">
              <div class="summary-label">
                <ha-icon icon="mdi:water" style="--mdc-icon-size:14px;color:#1976d2"></ha-icon>本期用水
              </div>
              <div class="summary-value">
                ${this._fmt(usage, 1)}<span class="summary-unit">m³</span>
              </div>
            </div>
            <div class="summary-item">
              <div class="summary-label">
                <ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px;color:#e65100"></ha-icon>本期费用
              </div>
              <div class="summary-value">
                ${this._fmt(bill)}<span class="summary-unit">元</span>
              </div>
            </div>
            <div class="summary-item">
              <div class="summary-label">
                <ha-icon icon="mdi:chart-bar" style="--mdc-icon-size:14px;color:#388e3c"></ha-icon>年累计用水
              </div>
              <div class="summary-value">
                ${this._fmt(annualUsage, 1)}<span class="summary-unit">m³</span>
              </div>
            </div>
          </div>

          <div class="details-section">
            <div class="details-title">
              <ha-icon icon="mdi:format-list-bulleted" style="--mdc-icon-size:14px"></ha-icon>费用明细（${readingMonth}）
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:water-outline" style="--mdc-icon-size:14px"></ha-icon>水费</span>
              <span class="detail-value">${this._fmt(waterFee)} 元</span>
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:water-pump" style="--mdc-icon-size:14px"></ha-icon>污水处理费</span>
              <span class="detail-value">${this._fmt(sewageFee)} 元</span>
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:trash-can-outline" style="--mdc-icon-size:14px"></ha-icon>垃圾处理费</span>
              <span class="detail-value">${this._fmt(garbageFee)} 元</span>
            </div>
            ${parseFloat(otherFees) > 0 ? html`
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:receipt-text-outline" style="--mdc-icon-size:14px"></ha-icon>其他费用</span>
              <span class="detail-value">${this._fmt(otherFees)} 元</span>
            </div>` : ""}
          </div>

          <div class="details-section" style="padding-top:0">
            <div class="details-title">
              <ha-icon icon="mdi:history" style="--mdc-icon-size:14px"></ha-icon>上次缴费
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:calendar" style="--mdc-icon-size:14px"></ha-icon>缴费日期</span>
              <span class="detail-value">${lastPayDate}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:cash-100" style="--mdc-icon-size:14px"></ha-icon>缴费金额</span>
              <span class="detail-value">${this._fmt(lastPayAmt)} 元</span>
            </div>
            <div class="detail-row">
              <span class="detail-label"><ha-icon icon="mdi:currency-cny" style="--mdc-icon-size:14px"></ha-icon>年累计水费</span>
              <span class="detail-value">${this._fmt(annualBill)} 元</span>
            </div>
          </div>

          <div class="update-time">${this._getUpdateTime()}</div>
        </ha-card>
      `;
    }
  }

  // 尝试从多个 Lit 来源初始化
  function initCard() {
    // 如果 LitElement 已可用，直接注册
    customElements.define("zhangjiajie-water-card", ZhangjiajieWaterCard);
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: "zhangjiajie-water-card",
      name: "张家界供水卡片",
      description: "显示张家界市自来水账单、余额、用水量等信息",
      preview: false,
      documentationURL: "https://github.com/yahooor/zhangjiajie_water_ha",
    });
    console.info("[zjwater-card] 卡片已注册");
  }

  // 检测 Lit 可用性后初始化
  if (LitElement) {
    initCard();
  } else {
    // 延迟加载：等待 HA 前端 Lit 加载完成
    import("https://unpkg.com/lit@2/index.js?module").then((lit) => {
      LitElement = lit.LitElement;
      html = lit.html;
      css = lit.css;
      // 用获取到的 Lit 重新定义 class
      console.info("[zjwater-card] Lit 从 CDN 加载成功");
      initCard();
    }).catch((err) => {
      console.warn("[zjwater-card] Lit 加载失败，尝试用原生 HTMLElement:", err);
      initCard();
    });
  }
})();
