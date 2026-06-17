import { useEffect, useState } from 'react'
import { AlertTriangle, Save, ShieldAlert, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import api from '../lib/api'
import { SETTING_FIELDS } from '../types'
import { SETTINGS_GLOSSARY } from '../lib/glossary'
import Panel from '../components/Panel'
import Modal from '../components/Modal'
import Tooltip from '../components/Tooltip'
import { cn } from '../lib/utils'

export default function Settings() {
  const [values, setValues] = useState<Record<string, number>>({})
  const [saving, setSaving] = useState(false)
  const [killActive, setKillActive] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [killPending, setKillPending] = useState(false)

  // Часть значений в БД хранится с float32-шумом (напр. 0.30000001192…).
  // Округляем до 6 знаков, чтобы поля были читаемыми; сохранение чинит и БД.
  const clean = (n: number) => Math.round((n + Number.EPSILON) * 1e6) / 1e6

  const loadKill = async () => {
    try {
      const { data } = await api.get('/api/v1/killswitch')
      setKillActive(Boolean(data.active))
    } catch {
      /* нет связи с executor — оставляем как есть */
    }
  }

  useEffect(() => {
    api
      .get('/api/v1/settings')
      .then(({ data }) => {
        const next: Record<string, number> = {}
        for (const f of SETTING_FIELDS) next[f.key] = clean(Number(data[f.key] ?? 0))
        setValues(next)
      })
      .catch(() => toast.error('Не удалось загрузить настройки'))
    loadKill()
  }, [])

  const setField = (key: string, raw: string) => {
    setValues((prev) => ({ ...prev, [key]: raw === '' ? 0 : Number(raw) }))
  }

  const save = async () => {
    setSaving(true)
    try {
      await api.put('/api/v1/settings', values)
      toast.success('Настройки сохранены')
    } catch {
      toast.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const confirmKill = async () => {
    const next = !killActive
    setKillPending(true)
    try {
      await api.post('/api/v1/killswitch', { active: next, reason: 'dashboard' })
      setKillActive(next)
      toast[next ? 'warning' : 'success'](next ? 'Kill switch включён — торговля остановлена' : 'Kill switch выключен — торговля возобновлена')
      setModalOpen(false)
    } catch {
      toast.error('Не удалось переключить kill switch (executor недоступен)')
    } finally {
      setKillPending(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Settings</h1>

      <Panel
        title="Параметры торговли и алертов"
        right={
          <button
            onClick={save}
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-page transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <Save size={15} />
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        }
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SETTING_FIELDS.map((f) => (
            <label key={f.key} className="flex flex-col gap-1">
              <span className="text-sm text-ink">
                <Tooltip text={SETTINGS_GLOSSARY[f.key] || f.hint}>{f.label}</Tooltip>
              </span>
              <div className="flex items-center rounded-lg border border-edge bg-surface2 focus-within:border-accent">
                <input
                  type="number"
                  step={f.step}
                  value={values[f.key] ?? ''}
                  onChange={(e) => setField(f.key, e.target.value)}
                  className="w-full bg-transparent px-3 py-2 text-sm text-ink outline-none"
                />
                <span className="px-3 text-xs text-muted">{f.unit}</span>
              </div>
              <span className="text-xs text-muted">{f.hint}</span>
            </label>
          ))}
        </div>
      </Panel>

      <Panel title="Аварийная остановка">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                'mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg',
                killActive ? 'bg-danger/15 text-danger' : 'bg-success/15 text-success',
              )}
            >
              {killActive ? <ShieldAlert size={18} /> : <ShieldCheck size={18} />}
            </span>
            <div>
              <div className="text-sm font-medium text-ink">
                Kill switch: {killActive ? 'ВКЛЮЧЁН' : 'выключен'}
              </div>
              <div className="text-xs text-muted">
                {killActive
                  ? 'Executor не создаёт новые сделки. Возобновите торговлю, когда будете готовы.'
                  : 'Торговля активна. Включите, чтобы немедленно остановить исполнение сделок.'}
              </div>
            </div>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className={cn(
              'rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90',
              killActive ? 'bg-success text-page' : 'bg-danger text-white',
            )}
          >
            {killActive ? 'Возобновить торговлю' : 'Остановить торговлю'}
          </button>
        </div>
      </Panel>

      <Modal
        open={modalOpen}
        title={killActive ? 'Возобновить торговлю?' : 'Остановить торговлю?'}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button
              onClick={() => setModalOpen(false)}
              className="rounded-lg border border-edge px-4 py-2 text-sm text-muted transition-colors hover:text-ink"
            >
              Отмена
            </button>
            <button
              onClick={confirmKill}
              disabled={killPending}
              className={cn(
                'rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50',
                killActive ? 'bg-success' : 'bg-danger',
              )}
            >
              {killPending ? '…' : killActive ? 'Да, возобновить' : 'Да, остановить'}
            </button>
          </>
        }
      >
        <div className="flex gap-3">
          <AlertTriangle size={18} className={killActive ? 'text-success' : 'text-danger'} />
          <p>
            {killActive
              ? 'Executor снова начнёт создавать сделки по входящим opportunities.'
              : 'Executor немедленно прекратит создавать новые сделки. Уже открытые расчёты не затрагиваются.'}
          </p>
        </div>
      </Modal>
    </div>
  )
}
