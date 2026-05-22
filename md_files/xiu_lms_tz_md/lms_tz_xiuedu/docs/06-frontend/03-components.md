# 03. Components (Komponentlar Kutubxonasi)

## Maqsad

Qayta ishlatiladigan UI komponentlar to'plami.

## Tuzilish

```
src/components/
├── ui/                    # Asosiy UI primitivlar
│   ├── Button.vue
│   ├── Input.vue
│   ├── Select.vue
│   ├── Textarea.vue
│   ├── Checkbox.vue
│   ├── Radio.vue
│   ├── Switch.vue
│   ├── Modal.vue
│   ├── Drawer.vue
│   ├── Tooltip.vue
│   ├── Popover.vue
│   ├── Card.vue
│   ├── Badge.vue
│   ├── Tag.vue
│   ├── Alert.vue
│   ├── Toast.vue
│   ├── Skeleton.vue
│   ├── Spinner.vue
│   ├── Avatar.vue
│   ├── Tabs.vue
│   ├── Accordion.vue
│   ├── Pagination.vue
│   ├── Breadcrumb.vue
│   ├── Stepper.vue
│   └── ...
├── layout/                # Layout komponentlar
│   ├── Sidebar.vue
│   ├── Topbar.vue
│   ├── Footer.vue
│   ├── PageHeader.vue
│   └── Container.vue
├── data/                  # Ma'lumot ko'rsatish
│   ├── DataTable.vue
│   ├── DataList.vue
│   ├── EmptyState.vue
│   ├── ErrorState.vue
│   └── ...
├── form/                  # Forms
│   ├── FormField.vue
│   ├── FileUpload.vue
│   ├── DatePicker.vue
│   ├── RichTextEditor.vue
│   └── ...
├── chart/                 # Charts
│   ├── BarChart.vue
│   ├── LineChart.vue
│   ├── PieChart.vue
│   └── ...
└── domain/                # Domain-specific
    ├── courses/
    ├── exams/
    ├── payments/
    └── ...
```

## Asosiy komponentlar

### Button

```vue
<!-- src/components/ui/Button.vue -->
<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'link'
  size?: 'xs' | 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  block?: boolean        // full-width
  iconLeft?: string
  iconRight?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const variantClass = computed(() => ({
  primary: 'bg-primary-600 hover:bg-primary-700 text-white',
  secondary: 'bg-secondary-600 hover:bg-secondary-700 text-white',
  outline: 'border border-gray-300 hover:bg-gray-50 text-gray-700',
  ghost: 'hover:bg-gray-100 text-gray-700',
  danger: 'bg-danger-600 hover:bg-danger-700 text-white',
  link: 'text-primary-600 hover:underline',
}[props.variant]))

const sizeClass = computed(() => ({
  xs: 'px-2 py-1 text-xs',
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
}[props.size]))
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors',
      'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      variantClass,
      sizeClass,
      block && 'w-full',
    ]"
    @click="emit('click', $event)"
  >
    <Spinner v-if="loading" class="w-4 h-4" />
    <Icon v-else-if="iconLeft" :name="iconLeft" class="w-4 h-4" />
    <slot />
    <Icon v-if="iconRight" :name="iconRight" class="w-4 h-4" />
  </button>
</template>
```

### Input

```vue
<!-- src/components/ui/Input.vue -->
<script setup lang="ts">
interface Props {
  modelValue?: string | number
  type?: string
  placeholder?: string
  label?: string
  error?: string
  helperText?: string
  disabled?: boolean
  required?: boolean
  iconLeft?: string
  iconRight?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  blur: []
}>()
</script>

<template>
  <div class="space-y-1">
    <label v-if="label" class="block text-sm font-medium text-gray-700">
      {{ label }}
      <span v-if="required" class="text-danger-500">*</span>
    </label>
    
    <div class="relative">
      <Icon
        v-if="iconLeft"
        :name="iconLeft"
        class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
      />
      
      <input
        :type="type || 'text'"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="[
          'block w-full rounded-md border-gray-300 shadow-sm',
          'focus:border-primary-500 focus:ring-primary-500',
          'disabled:bg-gray-50 disabled:text-gray-500',
          iconLeft && 'pl-10',
          iconRight && 'pr-10',
          error && 'border-danger-300 focus:border-danger-500 focus:ring-danger-500',
        ]"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @blur="emit('blur')"
      />
      
      <Icon
        v-if="iconRight"
        :name="iconRight"
        class="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
      />
    </div>
    
    <p v-if="error" class="text-sm text-danger-600">{{ error }}</p>
    <p v-else-if="helperText" class="text-sm text-gray-500">{{ helperText }}</p>
  </div>
</template>
```

### Modal

```vue
<!-- src/components/ui/Modal.vue -->
<script setup lang="ts">
import { Dialog, DialogPanel, DialogTitle, TransitionRoot, TransitionChild } from '@headlessui/vue'

interface Props {
  modelValue: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
  closeOnOverlay?: boolean
}

withDefaults(defineProps<Props>(), { size: 'md', closeOnOverlay: true })
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <TransitionRoot :show="modelValue" as="template">
    <Dialog @close="closeOnOverlay && close()" class="relative z-50">
      <TransitionChild
        enter="ease-out duration-200" enter-from="opacity-0" enter-to="opacity-100"
        leave="ease-in duration-150" leave-from="opacity-100" leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/40" />
      </TransitionChild>
      
      <div class="fixed inset-0 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <TransitionChild
            enter="ease-out duration-200" enter-from="opacity-0 scale-95" enter-to="opacity-100 scale-100"
            leave="ease-in duration-150" leave-from="opacity-100 scale-100" leave-to="opacity-0 scale-95"
          >
            <DialogPanel
              :class="[
                'rounded-lg bg-white shadow-xl w-full',
                {
                  sm: 'max-w-sm',
                  md: 'max-w-md',
                  lg: 'max-w-lg',
                  xl: 'max-w-xl',
                  '2xl': 'max-w-2xl',
                }[size]
              ]"
            >
              <div v-if="title || $slots.header" class="border-b px-6 py-4">
                <DialogTitle class="text-lg font-semibold">
                  <slot name="header">{{ title }}</slot>
                </DialogTitle>
              </div>
              
              <div class="p-6">
                <slot />
              </div>
              
              <div v-if="$slots.footer" class="border-t bg-gray-50 px-6 py-4">
                <slot name="footer" />
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
```

### DataTable

```vue
<!-- src/components/data/DataTable.vue -->
<script setup lang="ts">
interface Column<T = any> {
  key: string
  label: string
  sortable?: boolean
  render?: (row: T) => any
  width?: string
  align?: 'left' | 'center' | 'right'
}

interface Props<T = any> {
  columns: Column<T>[]
  rows: T[]
  loading?: boolean
  emptyText?: string
  pagination?: {
    page: number
    perPage: number
    total: number
  }
  selectable?: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  'sort': [key: string, direction: 'asc' | 'desc']
  'page-change': [page: number]
  'row-click': [row: any]
}>()
</script>

<template>
  <div class="overflow-hidden rounded-lg border bg-white">
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th v-if="selectable" class="px-4 py-3">
              <input type="checkbox" />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              :style="{ width: col.width }"
              :class="[
                'px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500',
                col.align === 'center' && 'text-center',
                col.align === 'right' && 'text-right',
                col.sortable && 'cursor-pointer hover:bg-gray-100',
              ]"
              @click="col.sortable && emit('sort', col.key, 'asc')"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        
        <tbody class="divide-y divide-gray-200 bg-white">
          <tr v-if="loading">
            <td :colspan="columns.length + (selectable ? 1 : 0)" class="px-4 py-8 text-center">
              <Spinner class="mx-auto" />
            </td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td :colspan="columns.length + (selectable ? 1 : 0)" class="px-4 py-8 text-center text-gray-500">
              {{ emptyText || "Ma'lumot yo'q" }}
            </td>
          </tr>
          <tr
            v-else
            v-for="row in rows"
            :key="row.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="emit('row-click', row)"
          >
            <td v-if="selectable" class="px-4 py-3">
              <input type="checkbox" @click.stop />
            </td>
            <td
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-4 py-3 text-sm text-gray-900',
                col.align === 'center' && 'text-center',
                col.align === 'right' && 'text-right',
              ]"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ col.render ? col.render(row) : row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div v-if="pagination" class="flex justify-between items-center px-4 py-3 border-t">
      <div class="text-sm text-gray-700">
        {{ (pagination.page - 1) * pagination.perPage + 1 }}—{{ Math.min(pagination.page * pagination.perPage, pagination.total) }} / {{ pagination.total }}
      </div>
      <Pagination
        :current="pagination.page"
        :total="Math.ceil(pagination.total / pagination.perPage)"
        @change="(p) => emit('page-change', p)"
      />
    </div>
  </div>
</template>
```

### Card

```vue
<!-- src/components/ui/Card.vue -->
<script setup lang="ts">
interface Props {
  title?: string
  subtitle?: string
  padding?: boolean
}

withDefaults(defineProps<Props>(), { padding: true })
</script>

<template>
  <div class="rounded-lg border bg-white shadow-sm">
    <div v-if="title || $slots.header" class="border-b px-6 py-4">
      <slot name="header">
        <h3 class="text-lg font-semibold">{{ title }}</h3>
        <p v-if="subtitle" class="text-sm text-gray-500">{{ subtitle }}</p>
      </slot>
    </div>
    
    <div :class="padding && 'p-6'">
      <slot />
    </div>
    
    <div v-if="$slots.footer" class="border-t bg-gray-50 px-6 py-4">
      <slot name="footer" />
    </div>
  </div>
</template>
```

## Toast notifications

```typescript
// src/composables/useToast.ts
import { ref } from 'vue'

interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

const toasts = ref<Toast[]>([])

let nextId = 0

export function useToast() {
  function show(type: Toast['type'], message: string, duration = 3000) {
    const id = nextId++
    toasts.value.push({ id, type, message, duration })
    setTimeout(() => remove(id), duration)
  }
  
  function remove(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }
  
  return {
    toasts,
    success: (msg: string) => show('success', msg),
    error: (msg: string) => show('error', msg),
    warning: (msg: string) => show('warning', msg),
    info: (msg: string) => show('info', msg),
  }
}
```

## Foydalanish

```vue
<script setup>
import { Button, Card, DataTable, Modal } from '@/components/ui'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const showModal = ref(false)

function handleSave() {
  toast.success("Muvaffaqiyatli saqlandi")
}
</script>

<template>
  <Card title="Talabalar ro'yxati">
    <Button variant="primary" @click="showModal = true">Yangi qo'shish</Button>
    
    <DataTable
      :columns="columns"
      :rows="students"
      :pagination="{ page, perPage, total }"
      @page-change="onPageChange"
    />
  </Card>
  
  <Modal v-model="showModal" title="Yangi talaba">
    <!-- form -->
    <template #footer>
      <Button @click="handleSave">Saqlash</Button>
    </template>
  </Modal>
</template>
```

## Acceptance kriteriyalar

- [ ] 30+ asosiy UI komponent
- [ ] Tailwind ustida qurilgan
- [ ] TypeScript bilan to'liq tipli
- [ ] Headless UI (a11y uchun)
- [ ] Dark mode qo'llab-quvvatlash
- [ ] Loading va empty states
- [ ] Storybook (komponentlarni ko'rsatish)
- [ ] Test coverage ≥ 70%
