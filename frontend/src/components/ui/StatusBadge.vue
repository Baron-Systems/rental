<template>
  <span class="badge-premium" :class="classMap[status] || classMap.default">
    <span class="w-1.5 h-1.5 rounded-full" :class="dotMap[status] || dotMap.default"></span>
    {{ label || labelMap[status] || status }}
  </span>
</template>

<script setup>
defineProps({
  status: { type: String, required: true },
  label: { type: String, default: '' },
})

const labelMap = {
  active: 'نشط',
  inactive: 'معطل',
  draft: 'مسودة',
  approved: 'معتمد',
  cancelled: 'ملغي',
  expired: 'منتهي',
  upcoming: 'قادم',
  evicted: 'تم الإخلاء',
  archived: 'مؤرشف',
  cash: 'نقداً',
  cheque: 'شيك',
  pending: 'قيد الانتظار',
  completed: 'مكتمل',
  empty: 'فارغة',
  rented: 'مؤجرة',
  reserved: 'محجوزة',
  unavailable: 'غير متاحة',
}

const classMap = {
  default: 'bg-ivory-200 text-navy-600 border-ivory-300',
  active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  inactive: 'bg-gray-100 text-gray-600 border-gray-200',
  draft: 'bg-amber-50 text-amber-700 border-amber-200',
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  upcoming: 'bg-blue-50 text-blue-700 border-blue-200',
  cancelled: 'bg-red-50 text-red-700 border-red-200',
  expired: 'bg-gray-100 text-gray-600 border-gray-200',
  evicted: 'bg-red-50 text-red-700 border-red-200',
  archived: 'bg-purple-50 text-purple-700 border-purple-200',
  cash: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  cheque: 'bg-blue-50 text-blue-700 border-blue-200',
  empty: 'bg-gray-100 text-gray-600 border-gray-200',
  rented: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  reserved: 'bg-amber-50 text-amber-700 border-amber-200',
  unavailable: 'bg-red-50 text-red-700 border-red-200',
}

const dotMap = {
  default: 'bg-navy-400',
  active: 'bg-emerald-500',
  approved: 'bg-emerald-500',
  completed: 'bg-emerald-500',
  inactive: 'bg-gray-400',
  draft: 'bg-amber-500',
  pending: 'bg-amber-500',
  upcoming: 'bg-blue-500',
  cancelled: 'bg-red-500',
  expired: 'bg-gray-400',
  evicted: 'bg-red-500',
  archived: 'bg-purple-500',
  cash: 'bg-emerald-500',
  cheque: 'bg-blue-500',
  empty: 'bg-gray-400',
  rented: 'bg-emerald-500',
  reserved: 'bg-amber-500',
  unavailable: 'bg-red-500',
}
</script>
