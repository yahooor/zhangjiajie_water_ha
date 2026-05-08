/**
 * 张家界供水 Lovelace 卡片
 * 无需构建，纯 LitElement + CSS
 * version: 3.0.0
 */
import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit@2/index.js?module";

class ZhangjiajieWaterCard extends LitElement {
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
  }

  setConfig(config) {
    if (!config.entity_prefix && !config.account) {
      throw new Error("请在卡片配置中指定 entity_prefix 或 account（户号末4位）");
    }
    this.config = config;
  }

  static get styles() {
    return css`
      :host {
        display: block;
        --card-bg: var(--ha-card-background, var(--card-background-color, #fff));
        --primary: #1565c0;
        --accent: #42a5f5;
        --text: var(--primary-text-color, #212121);
        --text-secondary: var(--secondary-text-color, #727272);
        --divider: var(--divider-color, rgba(0,0,0,0.12));
        --warning: #ff6f00;
      }
      ha-card {
        padding: 0;
        overflow: hidden;
        border-radius: 12px;
      }
      .header {
        background: linear-gradient(135deg, var(--primary), var(--accent));
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
        gap: 0;
        border-bottom: 1px solid var(--divider);
      }
      .summary-item {
        padding: 14px 16px;
        border-right: 1px solid var(--divider);
        border-bottom: 1px solid var(--divider);
      }
      .summary-item:nth-child(2n) {
        border-right: none;
      }
      .summary-item:nth-last-child(-n+2) {
        border-bottom: none;
      }
      .summary-label {
        font-size: 0.72em;
        color: var(--text-secondary);
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .summary-value {
        font-size: 1.2em;
        font-weight: 700;
        color: var(--text);
        line-height: 1.1;
      }
      .summary-value.highlight {
        color: var(--primary);
      }
      .summary-unit {
        font-size: 0.65em;
        font-weight: 400;
        color: var(--text-secondary);
        margin-left: 2px;
      }
      .details-section {
        padding: 12px 16px;
      }
      .details-title {
        font-size: 0.75em;
        font-weight: 600;
        color: var(--text-secondary);
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
        border-bottom: 1px solid var(--divider);
        font-size: 0.85em;
      }
      .detail-row:last-child {
        border-bottom: none;
      }
      .detail-label {
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        gap: 5px;
      }
      .detail-value {
        color: var(--text);
        font-weight: 500;
      }
      .unavailable {
        color: var(--text-secondary);
        font-style: italic;
      }
      .update-time {
        font-size: 0.7em;
        color: var(--text-secondary);
        text-align: right;
        padding: 6px 16px 10px;
      }
    `;
  }

  _getEntityId(key) {
    const prefix = this.config.entity_prefix || `sensor.zhang_jia_jie_gong_shui_${this.config.account}`;
    return `${prefix}_${key}`;
  }

  _getState(key) {
    const entityId = this._getEntityId(key);
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
      // 提取户号信息
      return entity.attributes.friendly_name.replace("账户余额", "").trim() || "张家界供水";
    }
    return this.config.title || "张家界供水";
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
      // 查找刷新按钮实体并调用 press 服务
      const btnEntity = Object.keys(this.hass.states).find(
        id => id.startsWith("button.") && id.includes("refresh") && id.includes(
          this.config.entity_prefix?.split(".")[1]?.split("_balance")[0] || "zhangjiajie"
        )
      );
      if (btnEntity) {
        await this.hass.callService("button", "press", { entity_id: btnEntity });
      } else {
        // 回退：直接更新协调器（触发 homeassistant.update_entity）
        const balanceId = this._getEntityId("balance");
        await this.hass.callService("homeassistant", "update_entity", { entity_id: balanceId });
      }
      // 等待 2 秒让数据刷新
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
    if (!this.hass || !this.config) return html``;

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
              <ha-icon icon="mdi:cash" style="--mdc-icon-size:14px;color:var(--primary)"></ha-icon>账户余额
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

customElements.define("zhangjiajie-water-card", ZhangjiajieWaterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "zhangjiajie-water-card",
  name: "张家界供水卡片",
  description: "显示张家界市自来水账单、余额、用水量等信息",
  preview: false,
  documentationURL: "https://github.com/yahooor/zhangjiajie_water_ha",
});
