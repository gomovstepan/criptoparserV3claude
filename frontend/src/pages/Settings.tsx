import { useCallback, useEffect, useId, useState } from 'react'
import { AlertTriangle, Save, ServerCrash, ShieldAlert, ShieldCheck, Wallet } from 'lucide-react'
import { toast } from 'sonner'
import api, { parseValidationErrors } from '../lib/api'
import { EXCHANGE_LIST, SETTING_FIELDS } from '../types'
import { SETTINGS_GLOSSARY } from '../lib/glossary'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import Panel from '../components/Panel'
import Modal from '../components/Modal'
import Tooltip from '../components/Tooltip'
import Button from '../components/Button'
import EmptyState from '../components/EmptyState'
import { asArray, cn } from '../lib/utils'

interface BalanceItem {
  exchange: string
  asset: string
  amount: number
}

export default function Settings() {
  useDocumentTitle('Settings')

  const fieldPrefix = useId()
  const balancePrefix = useId()

  const [values, setValues] = useState<Record<string, number>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [loadFailed, setLoadFailed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [killActive, setKillActive] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [killPending, setKillPending] = useState(false)
  const [paper, setPaper] = useState(false)
  const [balances, setBalances] = useState<Record<string, number>>({})
  const [balanceErrors, setBalanceErrors] = useState<Record<string, string>>({})
  const [savingBalances, setSavingBalances] = useState(false)

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

  const loadBalances = async () => {
    try {
      const { data } = await api.get<{ items: BalanceItem[] }>('/api/v1/balance')
      const map: Record<string, number> = {}
      for (const it of asArray<BalanceItem>(data?.items)) map[it.exchange] = clean(it.amount)
      setBalances(map)
    } catch {
      toast.error('Не удалось загрузить балансы')
    }
  }

  const loadSettings = useCallback(async () => {
    try {
      const { data } = await api.get('/api/v1/settings')
      const next: Record<string, number> = {}
      for (const f of SETTING_FIELDS) next[f.key] = clean(Number(data[f.key] ?? 0))
      setValues(next)
      setLoadFailed(false)
    } catch {
      setLoadFailed(true)
      toast.error('Не удалось загрузить настройки')
    }
  }, [])

  useEffect(() => {
    loadSettings()
    loadKill()
    api
      .get<{ paper: boolean }>('/api/v1/config')
      .then(({ data }) => {
        setPaper(Boolean(data.paper))
        if (data.paper) loadBalances()
      })
      .catch(() => {
        /* нет /config — считаем, что не paper, панель балансов скрыта */
      })
  }, [loadSettings])

  const setField = (key: string, raw: string) => {
    setValues((prev) => ({ ...prev, [key]: raw === '' ? 0 : Number(raw) }))
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: '' } : prev))
  }

  const setBalance = (exchange: string, raw: string) => {
    setBalances((prev) => ({ ...prev, [exchange]: raw === '' ? 0 : Number(raw) }))
    setBalanceErrors((prev) => (prev[exchange] ? { ...prev, [exchange]: '' } : prev))
  }

  const save = async () => {
    // Проверяем ДО отправки и показываем ошибку у поля, а не одним тостом сверху
    const errs: Record<string, string> = {}
    for (const f of SETTING_FIELDS) {
      const v = values[f.key]
      if (v == null || Number.isNaN(v)) errs[f.key] = 'Введите число'
      else if (v < 0 && !f.allowNegative) errs[f.key] = 'Значение не может быть отрицательным'
    }
    setFieldErrors(errs)
    if (Object.keys(errs).length > 0) {
      document.getElementById(`${fieldPrefix}-${Object.keys(errs)[0]}`)?.focus()
      return
    }

    setSaving(true)
    try {
      const { data } = await api.put('/api/v1/settings', values)
      // Сервер обновляет только существующие в БД строки: ключ без строки
      // возвращается в not_found, и молчаливый «успех» скрывал бы, что
      // гейты сейфти не применились (нужна миграция migrate-trading-gates.sql).
      const missing: string[] = data?.not_found ?? []
      if (missing.length > 0) {
        toast.warning(`Не применены (нет строк в БД): ${missing.join(', ')}`)
      } else {
        toast.success('Настройки сохранены')
      }
    } catch (err) {
      // 422 от api-gateway: сервер проверяет диапазоны (Pydantic, роутер
      // exchanges.py) строже, чем клиент. Раскладываем ошибки по полям тем же
      // механизмом fieldErrors, каким пользуется клиентская проверка выше.
      const serverErrs = parseValidationErrors(err)
      if (Object.keys(serverErrs).length > 0) {
        setFieldErrors(serverErrs)
        document.getElementById(`${fieldPrefix}-${Object.keys(serverErrs)[0]}`)?.focus()
        toast.error('Сервер отклонил некоторые значения')
      } else {
        toast.error('Ошибка сохранения')
      }
    } finally {
      setSaving(false)
    }
  }

  const saveBalances = async () => {
    const errs: Record<string, string> = {}
    for (const ex of EXCHANGE_LIST) {
      const v = balances[ex]
      if (v == null || Number.isNaN(v)) errs[ex] = 'Введите число'
      else if (v < 0) errs[ex] = 'Баланс не может быть отрицательным'
    }
    setBalanceErrors(errs)
    if (Object.keys(errs).length > 0) {
      document.getElementById(`${balancePrefix}-${Object.keys(errs)[0]}`)?.focus()
      return
    }

    setSavingBalances(true)
    try {
      await api.put('/api/v1/balance', { balances })
      toast.success('Балансы применены')
    } catch {
      toast.error('Не удалось применить балансы')
    } finally {
      setSavingBalances(false)
    }
  }

  const confirmKill = async () => {
    const next = !killActive
    setKillPending(true)
    try {
      await api.post('/api/v1/killswitch', { active: next, reason: 'dashboard' })
      setKillActive(next)
      toast[next ? 'warning' : 'success'](
        next ? 'Kill switch включён — торговля остановлена' : 'Kill switch выключен — торговля возобновлена',
      )
      setModalOpen(false)
    } catch {
      toast.error('Не удалось переключить kill switch (executor недоступен)')
    } finally {
      setKillPending(false)
    }
  }

  const numberInputClass = (invalid?: string) =>
    cn(
      'flex min-h-[44px] items-center rounded-lg border bg-surface2 focus-within:border-accent',
      invalid ? 'border-danger' : 'border-edge-strong',
    )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Settings</h1>

      <Panel
        title="Параметры торговли и алертов"
        right={
          <Button variant="primary" size="sm" onClick={save} loading={saving} loadingText="Сохранение…">
            <Save size={15} aria-hidden="true" />
            Сохранить
          </Button>
        }
      >
        {loadFailed && Object.keys(values).length === 0 ? (
          <EmptyState
            tone="danger"
            icon={ServerCrash}
            title="Не удалось загрузить настройки"
            hint="Запрос к /api/v1/settings не выполнен."
            onRetry={loadSettings}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SETTING_FIELDS.map((f) => {
              const id = `${fieldPrefix}-${f.key}`
              const err = fieldErrors[f.key]
              return (
                <div key={f.key} className="flex flex-col gap-1">
                  <label htmlFor={id} className="text-sm text-ink">
                    <Tooltip text={SETTINGS_GLOSSARY[f.key] || f.hint}>{f.label}</Tooltip>
                  </label>
                  <div className={numberInputClass(err)}>
                    <input
                      id={id}
                      type="number"
                      inputMode="decimal"
                      min={f.allowNegative ? undefined : 0}
                      step={f.step}
                      value={values[f.key] ?? ''}
                      onChange={(e) => setField(f.key, e.target.value)}
                      aria-invalid={err ? true : undefined}
                      aria-describedby={err ? `${id}-err` : `${id}-hint`}
                      className="w-full bg-transparent px-3 py-2 text-sm text-ink"
                    />
                    <span className="px-3 text-xs text-muted" aria-hidden="true">
                      {f.unit}
                    </span>
                  </div>
                  {err ? (
                    <span id={`${id}-err`} role="alert" className="text-xs text-danger">
                      {err}
                    </span>
                  ) : (
                    <span id={`${id}-hint`} className="text-xs text-muted">
                      {f.hint}, {f.unit}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Panel>

      {paper && (
        <Panel
          title="Балансы бирж (paper)"
          right={
            <Button
              variant="primary"
              size="sm"
              onClick={saveBalances}
              loading={savingBalances}
              loadingText="Применение…"
            >
              <Wallet size={15} aria-hidden="true" />
              Применить балансы
            </Button>
          }
        >
          <p className="mb-3 text-xs text-muted">
            Виртуальные USDT-балансы для симуляции. Размер позиции считается как max_position_pct% от
            баланса buy-биржи; правила исполнения те же, что и при настоящей торговле.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {EXCHANGE_LIST.map((ex) => {
              const id = `${balancePrefix}-${ex}`
              const err = balanceErrors[ex]
              return (
                <div key={ex} className="flex flex-col gap-1">
                  <label htmlFor={id} className="text-sm capitalize text-ink">
                    {ex}
                  </label>
                  <div className={numberInputClass(err)}>
                    <input
                      id={id}
                      type="number"
                      inputMode="decimal"
                      min={0}
                      step={1}
                      value={balances[ex] ?? ''}
                      onChange={(e) => setBalance(ex, e.target.value)}
                      aria-invalid={err ? true : undefined}
                      aria-describedby={err ? `${id}-err` : undefined}
                      className="w-full bg-transparent px-3 py-2 text-sm text-ink"
                    />
                    <span className="px-3 text-xs text-muted" aria-hidden="true">
                      USDT
                    </span>
                  </div>
                  {err && (
                    <span id={`${id}-err`} role="alert" className="text-xs text-danger">
                      {err}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </Panel>
      )}

      <Panel title="Аварийная остановка">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                killActive ? 'bg-danger/15 text-danger' : 'bg-success/15 text-success',
              )}
            >
              {killActive ? (
                <ShieldAlert size={18} aria-hidden="true" />
              ) : (
                <ShieldCheck size={18} aria-hidden="true" />
              )}
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
          <Button
            variant={killActive ? 'success' : 'danger'}
            onClick={() => setModalOpen(true)}
            className="shrink-0"
          >
            {killActive ? 'Возобновить торговлю' : 'Остановить торговлю'}
          </Button>
        </div>
      </Panel>

      <Modal
        open={modalOpen}
        title={killActive ? 'Возобновить торговлю?' : 'Остановить торговлю?'}
        onClose={() => !killPending && setModalOpen(false)}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)} disabled={killPending}>
              Отмена
            </Button>
            <Button
              variant={killActive ? 'success' : 'danger'}
              onClick={confirmKill}
              loading={killPending}
              loadingText="Применяем…"
            >
              {killActive ? 'Да, возобновить' : 'Да, остановить'}
            </Button>
          </>
        }
      >
        <div className="flex gap-3">
          <AlertTriangle
            size={18}
            aria-hidden="true"
            className={cn('mt-0.5 shrink-0', killActive ? 'text-success' : 'text-danger')}
          />
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
