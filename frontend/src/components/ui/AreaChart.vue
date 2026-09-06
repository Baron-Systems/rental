<template>
  <div class="w-full relative">
    <!-- Legend (top-left, circle icons — matches original) -->
    <div class="flex items-center gap-4 pb-3 text-[13px] font-semibold text-navy-900">
      <div class="flex items-center gap-1.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full" :style="{ background: colors.dues }"></span>
        <span>المستحقات</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full" :style="{ background: colors.receipts }"></span>
        <span>صافي التحصيل</span>
      </div>
    </div>

    <svg
      ref="svgRef"
      :viewBox="`0 0 ${vbW} ${vbH}`"
      class="w-full"
      style="height: 260px;"
      preserveAspectRatio="none"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
    >
      <defs>
        <linearGradient :id="duesGradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" :stop-color="colors.dues" stop-opacity="0.06" />
          <stop offset="95%" :stop-color="colors.dues" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="receiptsGradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" :stop-color="colors.receipts" stop-opacity="0.06" />
          <stop offset="95%" :stop-color="colors.receipts" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- Grid lines (horizontal dashed) -->
      <g>
        <line
          v-for="gy in gridYs"
          :key="'g' + gy"
          :x1="padL"
          :x2="vbW - padR"
          :y1="gy"
          :y2="gy"
          :stroke="colors.border"
          stroke-dasharray="3 3"
        />
      </g>

      <!-- Y axis labels -->
      <g v-for="(yt, i) in yTicks" :key="'y' + i">
        <text
          :x="padL - 8"
          :y="yt.y + 4"
          text-anchor="end"
          :font-size="13"
          :fill="colors.graphite"
          font-weight="500"
        >{{ yt.label }}</text>
      </g>

      <!-- Zero line (only when negative values exist) -->
      <line
        v-if="minVal < 0"
        :x1="padL"
        :x2="vbW - padR"
        :y1="yAt(0)"
        :y2="yAt(0)"
        :stroke="colors.graphite"
        stroke-width="1"
        stroke-dasharray="2 2"
        opacity="0.4"
      />

      <!-- Dues area + line -->
      <path :d="duesAreaPath" :fill="`url(#${duesGradId})`" stroke="none" />
      <path :d="duesLinePath" fill="none" :stroke="colors.dues" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />

      <!-- Receipts area + line -->
      <path :d="receiptsAreaPath" :fill="`url(#${receiptsGradId})`" stroke="none" />
      <path :d="receiptsLinePath" fill="none" :stroke="colors.receipts" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />

      <!-- X axis labels -->
      <g v-for="(d, i) in data" :key="'x' + i">
        <text
          :x="xAt(i)"
          :y="vbH - padB + 20"
          text-anchor="middle"
          :font-size="13"
          :fill="colors.graphite"
          font-weight="500"
        >{{ d.name }}</text>
      </g>

      <!-- Hover indicator -->
      <g v-if="hoverIdx >= 0">
        <line
          :x1="xAt(hoverIdx)"
          :x2="xAt(hoverIdx)"
          :y1="padT"
          :y2="vbH - padB"
          :stroke="colors.border"
          stroke-width="1"
        />
        <circle :cx="xAt(hoverIdx)" :cy="yAt(data[hoverIdx].dues)" r="4" :fill="colors.dues" />
        <circle :cx="xAt(hoverIdx)" :cy="yAt(data[hoverIdx].receipts)" r="4" :fill="colors.receipts" />
      </g>
    </svg>

    <!-- Tooltip (matches original ChartTooltip style) -->
    <div
      v-if="hoverIdx >= 0"
      class="rounded-[14px] border border-ivory-300 bg-white px-4 py-3 shadow-soft-md pointer-events-none"
      :style="tooltipStyle"
    >
      <p class="text-xs font-medium text-navy-400 mb-1">{{ data[hoverIdx].name }}</p>
      <p class="text-sm font-semibold text-navy-900">المستحقات: {{ formatMoney(data[hoverIdx].dues, currency) }}</p>
      <p class="text-sm font-semibold text-navy-900">صافي التحصيل: {{ formatMoney(data[hoverIdx].receipts, currency) }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, getCurrentInstance } from 'vue'
import { formatMoney } from '@/composables/useApi'

const props = defineProps({
  data: { type: Array, required: true },
  colors: { type: Object, required: true },
  currency: { type: String, default: 'ILS' },
})

const uid = getCurrentInstance().uid
const duesGradId = `duesGrad-${uid}`
const receiptsGradId = `receiptsGrad-${uid}`

const svgRef = ref(null)
const hoverIdx = ref(-1)
const mouseX = ref(0)

const vbW = 600
const vbH = 260
const padL = 48
const padR = 16
const padT = 16
const padB = 36

const maxVal = computed(() => {
  const all = props.data.flatMap(d => [d.dues, d.receipts])
  const m = Math.max(...all, 0)
  // round up to nice number
  if (m === 0) return 1
  const pow = Math.pow(10, String(Math.floor(m)).length - 1)
  return Math.ceil(m / pow) * pow
})

const minVal = computed(() => {
  const all = props.data.flatMap(d => [d.dues, d.receipts])
  const m = Math.min(...all, 0)
  if (m >= 0) return 0
  const absM = Math.abs(m)
  const pow = Math.pow(10, String(Math.floor(absM)).length - 1)
  return -Math.ceil(absM / pow) * pow
})

const valRange = computed(() => maxVal.value - minVal.value || 1)

const xAt = (i) => {
  const n = props.data.length
  const w = vbW - padL - padR
  return padL + (w / (n - 1)) * i
}

const yAt = (val) => {
  const h = vbH - padT - padB
  const frac = (val - minVal.value) / valRange.value
  return padT + h - frac * h
}

const linePath = (key) => {
  return props.data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(d[key])}`).join(' ')
}

const areaPath = (key) => {
  const base = yAt(0)
  const top = props.data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(d[key])}`).join(' ')
  const last = xAt(props.data.length - 1)
  const first = xAt(0)
  return `${top} L ${last} ${base} L ${first} ${base} Z`
}

const duesLinePath = computed(() => linePath('dues'))
const receiptsLinePath = computed(() => linePath('receipts'))
const duesAreaPath = computed(() => areaPath('dues'))
const receiptsAreaPath = computed(() => areaPath('receipts'))

const gridYs = computed(() => {
  const h = vbH - padT - padB
  return [0, 0.25, 0.5, 0.75, 1].map(f => padT + h * f)
})

const yTicks = computed(() => {
  return gridYs.value.map((gy, i) => {
    const frac = 1 - (i / 4)
    return { y: gy, label: Math.round(minVal.value + valRange.value * frac) }
  })
})

const tooltipStyle = computed(() => {
  if (hoverIdx.value < 0) return {}
  // Position tooltip above the chart area, centered on hover point
  const svgEl = svgRef.value
  if (!svgEl) return {}
  const rect = svgEl.getBoundingClientRect()
  const xPx = (xAt(hoverIdx.value) / vbW) * rect.width
  const left = Math.min(Math.max(xPx, 60), rect.width - 60)
  return {
    position: 'absolute',
    left: left + 'px',
    top: '8px',
    transform: 'translateX(-50%)',
  }
})

function onMouseMove(e) {
  const rect = svgRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const ratio = x / rect.width
  const vbX = ratio * vbW
  const n = props.data.length
  const w = vbW - padL - padR
  const idx = Math.round(((vbX - padL) / w) * (n - 1))
  hoverIdx.value = Math.max(0, Math.min(n - 1, idx))
}

function onMouseLeave() {
  hoverIdx.value = -1
}
</script>
