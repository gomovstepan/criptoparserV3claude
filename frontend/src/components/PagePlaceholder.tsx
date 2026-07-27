import { Construction } from 'lucide-react'
import EmptyState from './EmptyState'

/** Временная заглушка страницы (реальное наполнение — в следующих фазах). */
export default function PagePlaceholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">{title}</h1>
      <div className="mt-6 rounded-xl border border-edge bg-surface p-4">
        {/* Иконка из Lucide вместо эмодзи 🚧: эмодзи зависят от шрифта системы
            и не поддаются темизации (правило no-emoji-icons). */}
        <EmptyState icon={Construction} title="Раздел в разработке" hint={`Наполнение появится на ${phase}.`} />
      </div>
    </div>
  )
}
