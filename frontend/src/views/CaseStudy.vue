<script setup>
import { ref } from 'vue'

const cases = {
  meizhuohua: {
    code: '603538',
    name: '美诺华',
    summary: '小市值化学制药，量先行→逐级突破三个前高→加速翻倍',
    highs: [
      { label: 'H1', date: '2026-01-26', price: '22.38', desc: '26年1月高点' },
      { label: 'H2', date: '2025-10-31', price: '23.83', desc: '25年10月高点' },
      { label: 'H3', date: '2025-08-14', price: '28.40', desc: '25年8月高点' },
    ],
    timeline: [
      { date: '2026-03-06', type: 'success', title: '量能启动', desc: '成交量460万→1549万(+3.4倍)，收22.31涨8.4%，主力进场信号' },
      { date: '2026-03-10', type: 'success', title: '突破前高H1', desc: '放量突破26年1月高点22.38，收23.27，当日量1207万' },
      { date: '2026-03-11~12', type: 'warning', title: '洗盘确认', desc: '量缩小幅回调(-1.24%/-1.25%)，不破突破位，主力未出货' },
      { date: '2026-03-13', type: 'success', title: '涨停突破前高H2', desc: '涨停突破25年10月31日高点23.83，收25.37，量2272万' },
      { date: '2026-03-16~24', type: 'warning', title: '高位横盘洗盘', desc: '震荡25-29区间，量缩换手，蓄力再突破' },
      { date: '2026-03-25', type: 'success', title: '突破前高H3', desc: '突破25年8月14日高点28.40，收32.38，量2916万' },
      { date: '2026-03-26~30', type: 'success', title: '加速拉升', desc: '连续三板：35.62→39.18→43.10，一个月涨幅超100%' },
    ],
    rules: [
      { tag: '量先行', color: 'success', desc: '放量日是启动信号，放量后量能不萎缩才是真启动' },
      { tag: '逐级突破', color: 'success', desc: '每突破一个前高后稳住，再向上一关，不跳跃' },
      { tag: '洗盘不破位', color: 'warning', desc: '每次回调只要不跌破上一个突破位，就继续持有' },
      { tag: '加速是信号', color: 'danger', desc: '连续涨停/成交量极度放大时，进入出场观察模式' },
    ],
    framework: [
      { action: '买入', condition: '放量突破前高后，次日确认不破支撑', risk: '适中' },
      { action: '持有', condition: '价格在支撑位上方，量缩不破位', risk: '低' },
      { action: '加仓', condition: '每突破一个新前高确认有效后', risk: '适中' },
      { action: '止损', condition: '收盘跌破上一突破位', risk: '—' },
      { action: '出场', condition: '出现大阴线+极大量，或连续缩量阴线', risk: '—' },
    ],
  },
  huahong: {
    code: '002645',
    name: '华宏科技',
    summary: '放量突破日最低价=关键支撑位，冲击失败不破支撑=主力未离场',
    highs: [
      { label: 'H1', date: '2025-06-12', price: '10.48', desc: '25年内高点' },
      { label: 'H2', date: '2024-04-03', price: '13.05', desc: '24年4月高点（≈23年7月12.64）' },
      { label: 'H3', date: '2023-04-18', price: '16.35', desc: '23年4月高点' },
      { label: 'H4', date: '2023-02-10', price: '20.59', desc: '历史高点' },
    ],
    timeline: [
      { date: '2025-07-11', type: 'success', title: '涨停启动，突破H1', desc: '涨停收10.45，突破H1(10.48)，量5122万' },
      { date: '2025-07-14~15', type: 'success', title: '跳空高开连续涨停', desc: '跳空高开无回调，11.50→12.65，强势站稳H1上方' },
      { date: '2025-07-16', type: 'success', title: '放量突破H2', desc: '平开放量破H2(13.05)，收13.92，量1.43亿。关键支撑锚定：当日最低12.87' },
      { date: '2025-07-17', type: 'danger', title: '跌停式洗盘', desc: '高开后砸跌，收13.03(-6.4%)，最低12.80，未破支撑12.87 ✅' },
      { date: '2025-07-18', type: 'success', title: '反包确认支撑', desc: '低开反包收14.33，最低12.95，再次确认12.87支撑有效' },
      { date: '2025-07-21', type: 'success', title: '冲击H3', desc: '涨停收15.76，逼近H3(16.35)' },
      { date: '2025-07-29~30', type: 'danger', title: '冲击H3失败', desc: '7.29未能站上16.35，7.30跌停收14.34' },
      { date: '2025-08-06', type: 'warning', title: '回踩不破关键支撑', desc: '最低12.91，全程未破7.16关键支撑12.87 ✅，量持续萎缩=吸筹' },
      { date: '2025-08-15~19', type: 'success', title: '新一波拉升，突破H3', desc: '三连板：14.92→16.41→18.05，H3(16.35)正式突破' },
    ],
    rules: [
      { tag: '支撑位锚定法', color: 'success', desc: '放量突破当日的最低价=该突破位的支撑底线，后续回踩不破则有效' },
      { tag: '冲击失败≠趋势结束', color: 'warning', desc: '冲击前高失败+跌停，只要不破上一关键支撑，主力没有离场' },
      { tag: '缩量是吸筹信号', color: 'success', desc: '价格跌不动+成交量持续萎缩=主力在低位接货，不是出货' },
      { tag: '突破方式判断强弱', color: '', desc: '跳空高开=极强/平开放量=主动攻击/缩量横盘后发力=充分蓄力' },
    ],
    framework: [
      { action: '买入', condition: '放量突破前高后次日确认不破支撑（当日最低价）', risk: '适中' },
      { action: '持有', condition: '价格守在关键支撑上方，量缩不破位', risk: '低' },
      { action: '冲击失败时', condition: '不破关键支撑→持有；破支撑→止损', risk: '—' },
      { action: '止损', condition: '收盘跌破放量突破日的最低价', risk: '—' },
      { action: '加仓', condition: '每突破一个新前高确认有效后', risk: '适中' },
    ],
  },

  taijia: {
    code: '002843',
    name: '泰嘉股份',
    summary: '快刀型拉升：H1突破后H2/H3同时被穿越，速战速决，需快进快出',
    highs: [
      { label: 'H1', date: '2026-01-08~27', price: '22.13', desc: '26年1月震荡高点' },
      { label: 'H2', date: '2025-09-19', price: '25.46', desc: '25年9月高点' },
      { label: 'H3', date: '2025-08-26', price: '26.59', desc: '25年8月高点' },
    ],
    timeline: [
      { date: '2026-02-13', type: 'success', title: '启动信号', desc: '涨停收20.85，量2278万（前日547万，放量4倍+），低位蓄力后启动' },
      { date: '2026-02-24~25', type: 'success', title: '放量冲击H1', desc: '2.25量爆4420万冲22.13未站稳，2.26涨停收22.97突破H1，关键支撑：当日最低21.58' },
      { date: '2026-02-27', type: 'success', title: '一字涨停，无洗盘', desc: '直接一字涨停收25.27，H1突破后完全不给低吸机会' },
      { date: '2026-03-02', type: 'success', title: '同时穿越H2+H3', desc: '涨停收27.80，一举突破H2(25.46)和H3(26.59)，多头极强' },
      { date: '2026-03-03', type: 'danger', title: '量能顶点，见顶信号', desc: '量爆1亿股（历史极值），收28.99，冲30.58后回落，高位见顶' },
      { date: '2026-03-05', type: 'danger', title: '跌停破H2支撑', desc: '直接跌停-10%，收25.39，跌破H2(25.46)，明确出场信号' },
      { date: '2026-03-06', type: 'warning', title: '反弹涨停，但趋势已变', desc: '涨停反弹收27.93，之后逐渐下行，不再创新高' },
      { date: '2026-03-12~13', type: 'danger', title: '持续下跌', desc: '收24.94→23.37，整波拉升结束' },
    ],
    rules: [
      { tag: '快刀型vs阶梯型', color: 'danger', desc: 'H2/H3同时被突破、中间无停留=主力赶时间，后续速度极快但持续性差' },
      { tag: '量能极值=顶部', color: 'danger', desc: '3.03成交量1亿股创历史新高，配合高位滞涨，是最强见顶信号' },
      { tag: '破H2即止损', color: 'warning', desc: '3.05跌停跌破H2支撑25.46，按华宏/美诺华规则，这是明确止损位' },
      { tag: '买点极窄', color: 'warning', desc: '2.26突破H1是唯一标准买点，2.27一字涨停无法买入，之后已是高位' },
    ],
    framework: [
      { action: '买入', condition: '2.26涨停突破H1（22.13）当天是唯一合理买点' },
      { action: '持有', condition: 'H2/H3突破时继续持有，但要高度警惕量能' },
      { action: '止损', condition: '跌破H2支撑(25.46)立即止损，不等反弹' },
      { action: '快刀规则', condition: '从突破到见顶仅6个交易日，不能用阶梯型思维慢慢拿' },
      { action: '风险提示', condition: '量能极值当天或次日需准备减仓，不贪最后一涨' },
    ],
  },

  shenjian: {
    code: '002361',
    name: '神剑股份',
    summary: '多波次拉升，冲击历史高点失败→回踩不破支撑→再次发力，当前逼近H6(18.13)关键压力位',
    highs: [
      { label: 'H4', date: '2025-08-05', price: '7.55', desc: '25年第二波高点' },
      { label: 'H5', date: '2025-12-26', price: '13.17', desc: '25年底连板高点' },
      { label: 'H6', date: '2026-01-14', price: '18.13', desc: '26年1月最高点（当前压力位）' },
    ],
    timeline: [
      { date: '2025-12-15', type: 'success', title: '第三大波启动', desc: '量爆1.07亿股，涨停收7.14，放量3倍+，启动信号' },
      { date: '2025-12-18~26', type: 'success', title: '七连板加速', desc: '7.43→8.17→8.99→9.89→10.88→11.97→13.17，突破H4/H5' },
      { date: '2025-12-30', type: 'danger', title: '高位见顶信号', desc: '巨量3.64亿股大跌-10%，量价背离，见顶' },
      { date: '2026-01-08~14', type: 'success', title: '最后一涨，H6确立', desc: '1.08涨停15.85，1.14最高18.13，H6高点确立' },
      { date: '2026-01-15~20', type: 'danger', title: '四连跌停崩落', desc: '18.13→11元，主力出货，量缩后低位横盘吸筹' },
      { date: '2026-01-27~03-25', type: 'warning', title: '低位横盘蓄力', desc: '11-13区间震荡，量持续萎缩，关键支撑3.26启动日最低11.19' },
      { date: '2026-03-26~31', type: 'success', title: '新一波四连板', desc: '3.26量爆1.58亿启动，四连板12.40→13.64→15.00→16.50' },
      { date: '2026-04-01', type: 'success', title: '冲击H6', desc: '高开冲18，盘中触及18.00，量4.09亿，逼近H6(18.13)' },
      { date: '2026-04-03~07', type: 'danger', title: '冲击H6失败回落', desc: '4.03放量大跌-9%，4.07继续跌，冲击失败信号' },
      { date: '2026-04-08~09', type: 'warning', title: '反弹震荡，方向未定', desc: '4.08涨停反包，4.09小跌，量仍大，多空博弈中' },
    ],
    rules: [
      { tag: '多波次结构', color: 'success', desc: '同一支票反复拉升，每次拉升前都有充分缩量洗盘，是主力长期运营的特征' },
      { tag: '历史高点即压力', color: 'warning', desc: 'H6(18.13)是1月高点，当前冲击失败，需等待突破确认才能追' },
      { tag: '关键支撑：15附近', color: 'success', desc: '3.30~3.31涨停区间，回踩若守住+缩量=下一波蓄力中' },
      { tag: '量能极大需警惕', color: 'danger', desc: '4.01量4.09亿极度放大，类似12.30见顶时的特征，需观察后续能否缩量企稳' },
    ],
    framework: [
      { action: '当前状态', condition: '冲击H6失败，高位震荡，方向未定' },
      { action: '买入条件', condition: '放量突破18.13并站稳，下一目标25+' },
      { action: '观望条件', condition: '在15-18区间震荡，量缩不破15支撑' },
      { action: '止损条件', condition: '跌破15（3.30~3.31涨停区支撑），说明这波拉升失败' },
      { action: '风险提示', condition: '4.01巨量冲顶未破，形态类似12.30见顶，需谨慎' },
    ],
  },
}

const activeTab = ref('meizhuohua')
</script>

<template>
  <div>
    <div style="margin-bottom:20px">
      <h2 style="margin:0;font-size:20px;color:#303133">📚 经典案例分析</h2>
      <p style="margin:6px 0 0;color:#909399;font-size:13px">基于真实行情复盘，提炼阶梯突破前高交易体系</p>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane v-for="(c, key) in cases" :key="key" :name="key" :label="`${c.name}（${c.code}）`">

        <!-- 基本信息 -->
        <el-alert :title="c.summary" type="info" :closable="false" style="margin-bottom:16px" />

        <!-- 前高列表 -->
        <el-card style="margin-bottom:16px">
          <template #header><span style="font-weight:600">📌 关键前高位置</span></template>
          <el-row :gutter="12">
            <el-col :span="6" v-for="h in c.highs" :key="h.label">
              <el-card shadow="never" style="text-align:center;background:#f8f9fa">
                <div style="font-size:18px;font-weight:bold;color:#e6a23c">{{ h.label }}</div>
                <div style="font-size:20px;font-weight:bold;color:#f56c6c;margin:4px 0">{{ h.price }}</div>
                <div style="font-size:12px;color:#909399">{{ h.date }}</div>
                <div style="font-size:12px;color:#606266;margin-top:4px">{{ h.desc }}</div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>

        <el-row :gutter="16">
          <!-- 时间线 -->
          <el-col :span="14">
            <el-card>
              <template #header><span style="font-weight:600">🕐 关键节点时间线</span></template>
              <el-timeline>
                <el-timeline-item
                  v-for="(item, i) in c.timeline"
                  :key="i"
                  :type="item.type"
                  :timestamp="item.date"
                  placement="top"
                >
                  <el-card shadow="never" :style="`border-left:3px solid ${item.type==='success'?'#67c23a':item.type==='danger'?'#f56c6c':'#e6a23c'};margin-bottom:4px`">
                    <div style="font-weight:600;font-size:14px;margin-bottom:4px">{{ item.title }}</div>
                    <div style="font-size:13px;color:#606266">{{ item.desc }}</div>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-col>

          <!-- 规律+框架 -->
          <el-col :span="10">
            <el-card style="margin-bottom:16px">
              <template #header><span style="font-weight:600">💡 核心规律</span></template>
              <div v-for="(r, i) in c.rules" :key="i" style="margin-bottom:12px">
                <el-tag :type="r.color || 'info'" style="margin-bottom:6px">{{ r.tag }}</el-tag>
                <div style="font-size:13px;color:#606266;line-height:1.6">{{ r.desc }}</div>
              </div>
            </el-card>

            <el-card>
              <template #header><span style="font-weight:600">📋 交易框架</span></template>
              <el-table :data="c.framework" size="small" border>
                <el-table-column prop="action" label="操作" width="80" align="center">
                  <template #default="{row}">
                    <el-tag size="small" :type="row.action==='止损'?'danger':row.action==='买入'||row.action==='加仓'?'success':'info'">{{ row.action }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="condition" label="条件" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>

      </el-tab-pane>
    </el-tabs>
  </div>
</template>
<!-- 神剑股份案例数据已通过script setup注入 -->
