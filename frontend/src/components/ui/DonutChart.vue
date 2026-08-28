<template>
  <div class="w-full">
    <svg viewBox="0 0 200 200" class="w-full" style="height: 170px;">
      <g v-for="(seg, i) in segments" :key="i">
        <path
          :d="seg.path"
          :fill="seg.fill"
          stroke="none"
        />
      </g>
      <circle v-if="total === 0" cx="100" cy="100" :r="outerR" :fill="colors.empty" opacity="0.15" />
    </svg>

    <!-- Legend below (matches original: circle + name: value) -->
    <div class="mt-4 flex items-center justify-center gap-4 flex-wrap">
      <div
        v-for="entry in data"
        :key="entry.name"
        class="flex items-center gap-1.5"
      >
        <span class="inline-block h-2.5 w-2.5 rounded-full" :style="{ background: entry.fill }"></span>
        <span class="text-sm text-navy-400">
          {{ entry.name }}: <span class="font-semibold text-navy-900">{{ entry.value }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, required: true },
})

const colors = {
  empty: '#94a3b8',
}

const cx = 100
const cy = 100
const innerR = 50
const outerR = 70
const paddingAngle = 3 // degrees

const total = computed(() => props.data.reduce((s, d) => s + (d.value || 0), 0))

const segments = computed(() => {
  if (total.value === 0) return []
  const segs = []
  let startAngle = -90 // start at top
  const gap = paddingAngle

  for (const entry of props.data) {
    const val = entry.value || 0
    if (val <= 0) continue
    const angle = (val / total.value) * 360
    const endAngle = startAngle + angle

    // Apply padding gap (shrink each segment by gap/2 on each side)
    const segStart = startAngle + gap / 2
    const segEnd = endAngle - gap / 2

    if (segEnd > segStart) {
      segs.push({
        path: donutPath(cx, cy, innerR, outerR, segStart, segEnd),
        fill: entry.fill,
      })
    }
    startAngle = endAngle
  }
  return segs
})

function polar(cx, cy, r, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function donutPath(cx, cy, ir, or_, startAngle, endAngle) {
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  const p1 = polar(cx, cy, or_, startAngle)
  const p2 = polar(cx, cy, or_, endAngle)
  const p3 = polar(cx, cy, ir, endAngle)
  const p4 = polar(cx, cy, ir, startAngle)
  return [
    `M ${p1.x} ${p1.y}`,
    `A ${or_} ${or_} 0 ${largeArc} 1 ${p2.x} ${p2.y}`,
    `L ${p3.x} ${p3.y}`,
    `A ${ir} ${ir} 0 ${largeArc} 0 ${p4.x} ${p4.y}`,
    'Z',
  ].join(' ')
}
</script>
