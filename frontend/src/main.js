import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'

import { Button, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

// Global components
app.component('Button', Button)
app.component('StatusBadge', () => import('@/components/ui/StatusBadge.vue'))
app.component('Card', () => import('@/components/ui/Card.vue'))
app.component('DataTable', () => import('@/components/ui/DataTable.vue'))
app.component('TableRow', () => import('@/components/ui/TableRow.vue'))
app.component('TableCell', () => import('@/components/ui/TableCell.vue'))
app.component('Modal', () => import('@/components/ui/Modal.vue'))
app.component('PageHeader', () => import('@/components/ui/PageHeader.vue'))
app.component('EmptyState', () => import('@/components/ui/EmptyState.vue'))
app.component('Pagination', () => import('@/components/ui/Pagination.vue'))
app.component('StatCard', () => import('@/components/ui/StatCard.vue'))
app.component('FormField', () => import('@/components/ui/FormField.vue'))
app.component('SearchableTenantSelect', () => import('@/components/ui/SearchableTenantSelect.vue'))

app.mount('#app')
