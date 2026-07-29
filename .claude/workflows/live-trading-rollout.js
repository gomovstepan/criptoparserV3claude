export const meta = {
  name: 'live-trading-rollout',
  description: 'Этапы 1-6 перехода на реальную торговлю: свежий агент на юнит, тесты, ревью, до 2 раундов автофиксов, коммит в ветку этапа',
  whenToUse: 'Запускать по явной просьбе пользователя. Задачи этапов — docs/live-trading/ROADMAP.md; контекст между этапами передаётся через отчёты docs/live-trading/stage-*-report.md, а не через сессию.',
  phases: [
    { title: 'Подготовка', detail: 'коммит хвостов, стек healthy, базовые тесты зелёные' },
    { title: 'Этап 1: Модель учёта' },
    { title: 'Этап 2: Слой исполнения', detail: '2A инфраструктура, 2B движок, 2C экономика' },
    { title: 'Этап 3: Риск-контуры' },
    { title: 'Этап 4: Качество данных' },
    { title: 'Этап 5: Наблюдаемость' },
    { title: 'Этап 6: Готовность к shadow' },
  ],
}

const REPO = '/home/projects/criptoparserV3claude'
const ROADMAP = 'docs/live-trading/ROADMAP.md'

const COMMON = [
  'Репозиторий: ' + REPO + ' (Linux VPS, docker compose стек). Отвечай на русском.',
  'Ты — самостоятельный агент дорожной карты перехода на реальную торговлю.',
  'ЕДИНСТВЕННЫЙ контекст: ' + ROADMAP + ' (раздел «Общее для агентов», «Конвенции и инварианты», твой раздел), CLAUDE.md, отчёты docs/live-trading/stage-*-report.md, сам код. Прочитай их ПРЕЖДЕ чем действовать.',
  'Нарушение инвариантов из ROADMAP/CLAUDE.md недопустимо.',
].join('\n')

const GATE = {
  type: 'object', required: ['ok', 'summary'], additionalProperties: false,
  properties: { ok: { type: 'boolean' }, summary: { type: 'string' } },
}

const FINDINGS = {
  type: 'object', required: ['findings'], additionalProperties: false,
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'file', 'title', 'detail', 'fix'],
        additionalProperties: false,
        properties: {
          severity: { enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          title: { type: 'string' },
          detail: { type: 'string', description: 'суть с цитатой кода — только проверенные факты' },
          fix: { type: 'string', description: 'конкретное исправление' },
        },
      },
    },
  },
}

const STAGES = [
  { num: 1, phase: 'Этап 1: Модель учёта', branch: 'live/stage-1', units: [
    { key: '1', section: 'Этап 1', skills: 'ecc:python-patterns, ecc:redis-patterns, ecc:postgres-patterns, ecc:database-migrations, ecc:tdd-workflow', reviewers: ['ecc:python-reviewer', 'ecc:database-reviewer'] },
  ] },
  { num: 2, phase: 'Этап 2: Слой исполнения', branch: 'live/stage-2', units: [
    { key: '2A', section: 'Этап 2A', skills: 'ecc:python-patterns, ecc:error-handling, ecc:security-review, ecc:tdd-workflow', reviewers: ['ecc:python-reviewer', 'ecc:security-reviewer'] },
    { key: '2B', section: 'Этап 2B', skills: 'ecc:python-patterns, ecc:latency-critical-systems, ecc:tdd-workflow', reviewers: ['ecc:python-reviewer'] },
    { key: '2C', section: 'Этап 2C', skills: 'ecc:python-patterns, ecc:tdd-workflow', reviewers: ['ecc:python-reviewer'] },
  ] },
  { num: 3, phase: 'Этап 3: Риск-контуры', branch: 'live/stage-3', units: [
    { key: '3', section: 'Этап 3', skills: 'ecc:python-patterns, ecc:tdd-workflow', reviewers: ['ecc:python-reviewer'] },
  ] },
  { num: 4, phase: 'Этап 4: Качество данных', branch: 'live/stage-4', units: [
    { key: '4', section: 'Этап 4', skills: 'ecc:python-patterns, ecc:redis-patterns', reviewers: ['ecc:python-reviewer'] },
  ] },
  { num: 5, phase: 'Этап 5: Наблюдаемость', branch: 'live/stage-5', units: [
    { key: '5', section: 'Этап 5', skills: 'ecc:docker-patterns, ecc:deployment-patterns, ecc:security-review', reviewers: ['ecc:code-reviewer', 'ecc:security-reviewer'] },
  ] },
  { num: 6, phase: 'Этап 6: Готовность к shadow', branch: 'live/stage-6', units: [
    { key: '6', section: 'Этап 6', skills: 'ecc:production-audit', reviewers: [] },
  ] },
]

function implPrompt(unit) {
  return COMMON + '\n\nТВОЯ ЗАДАЧА: реализовать раздел «' + unit.section + '» из ' + ROADMAP + ' целиком.\n'
    + 'Порядок:\n'
    + '1) Прочитай источники контекста (см. выше).\n'
    + '2) Загрузи скилы инструментом Skill: ' + unit.skills + ' (недоступный — пропусти).\n'
    + '3) Реализуй задачи раздела. Тесты пиши вместе с кодом (stdlib unittest; новые сьюты — в tests/run-tests.sh).\n'
    + '4) Пересобери затронутые сервисы (docker compose up -d --build <svc...>), добейся: контейнеры healthy, bash tests/run-tests.sh полностью зелёный.\n'
    + '5) Напиши отчёт docs/live-trading/stage-' + unit.key + '-report.md по шаблону из «Общее для агентов».\n'
    + '6) git НЕ трогай: не коммить, не создавай веток.\n'
    + 'Верни 10-20 строк: что сделано, что отложено и почему, статус тестов.'
}

function testGatePrompt() {
  return 'Репозиторий ' + REPO + '. Проверь: (1) docker compose ps — все контейнеры healthy (подожди until-циклом до 120с, если поднимаются); (2) bash tests/run-tests.sh — все сьюты OK. ok=true только если оба условия выполнены; при провале в summary — имена упавших сьютов и последние строки их вывода. Ничего не редактируй.'
}

function reviewPrompt(unit, round) {
  return 'Репозиторий ' + REPO + '. Раунд ревью ' + round + '. Проведи ревью НЕЗАКОММИЧЕННЫХ изменений рабочего дерева (git status; git diff; новые файлы читай целиком) этапа «' + unit.section + '» дорожной карты ' + ROADMAP + ' — прочитай его раздел и отчёт docs/live-trading/stage-' + unit.key + '-report.md, чтобы понимать намерения.\n'
    + 'Severity: CRITICAL — потеря денег, дыра безопасности или нарушение инвариантов из разделов «Конвенции и инварианты» (ROADMAP) и CLAUDE.md; HIGH — вероятный дефект/риск на реальной торговле; MEDIUM/LOW — качество.\n'
    + 'Каждый finding подтверждай file:line и цитатой — открой файл и проверь; не выдумывай проблем ради количества. Если замечаний нет — верни пустой список.'
}

function fixPrompt(unit, findings, reason) {
  return COMMON + '\n\nТВОЯ ЗАДАЧА: исправить перечисленные проблемы этапа «' + unit.section + '» (' + reason + '). Исправляй ТОЛЬКО их — не расширяй объём работ. После исправлений: пересобери затронутые сервисы, добейся зелёного bash tests/run-tests.sh, дополни отчёт docs/live-trading/stage-' + unit.key + '-report.md разделом об исправлениях. git не трогай.\n\nПроблемы:\n' + JSON.stringify(findings, null, 2)
}

function branchPrompt(branch) {
  return 'Репозиторий ' + REPO + '. Переключись на ветку ' + branch + ': если она существует — git checkout ' + branch + '; если нет — git checkout -b ' + branch + ' от текущего HEAD. Флаг -B НЕ используй (он сбрасывает существующую ветку). Убедись: git branch --show-current выводит ' + branch + '. Незакоммиченные изменения при переключении сохраняются (это ожидаемо). ok=true при успехе; в summary — имя ветки и HEAD.'
}

function commitPrompt(unit, branch) {
  return 'Репозиторий ' + REPO + '. Ты на ветке ' + branch + ' (проверь git branch --show-current; иначе ok=false). Закоммить ВСЕ изменения рабочего дерева: git add -A; git commit. Сообщение: первая строка «этап ' + unit.key + ': <суть по отчёту docs/live-trading/stage-' + unit.key + '-report.md>», затем пустая строка и строка: Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>. В summary верни hash коммита (git rev-parse --short HEAD).'
}

const from = Number((args && args.from) || 1)
const to = Number((args && args.to) || 6)

phase('Подготовка')
const prep = await agent(
  'Репозиторий ' + REPO + '. Подготовка к прогону этапов ' + from + '-' + to + ' дорожной карты ' + ROADMAP + ':\n'
  + '1) Файл ' + ROADMAP + ' существует и содержит разделы этапов (иначе ok=false).\n'
  + '2) Если git status показывает незакоммиченные изменения — это хвост завершённого этапа 0: git add -A и git commit в ТЕКУЩУЮ ветку, первая строка «этап 0: гигиена и сейфти (по аудиту)», затем пустая строка и Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>.\n'
  + '3) docker compose up -d; дождись healthy всех контейнеров (until-цикл, до 180с).\n'
  + '4) bash tests/run-tests.sh — все сьюты обязаны быть зелёными (иначе ok=false с выводом упавших).\n'
  + 'В summary: ветка, HEAD, статус стека и тестов.',
  { label: 'prep', phase: 'Подготовка', schema: GATE }
)
if (!prep || !prep.ok) return { stopped_at: 'prep', reason: prep ? prep.summary : 'prep agent failed' }
log('Подготовка: ' + prep.summary)

const done = []
for (const stage of STAGES) {
  if (stage.num < from || stage.num > to) continue
  phase(stage.phase)

  const br = await agent(branchPrompt(stage.branch), { label: 'branch:' + stage.branch, phase: stage.phase, schema: GATE, effort: 'low' })
  if (!br || !br.ok) return { stopped_at: stage.phase, reason: 'ветка: ' + (br ? br.summary : 'branch agent failed'), done }

  for (const unit of stage.units) {
    log('Юнит ' + unit.key + ': реализация')
    const impl = await agent(implPrompt(unit), { label: 'impl:' + unit.key, phase: stage.phase })
    if (impl === null) return { stopped_at: unit.key, reason: 'агент реализации не завершился', done }

    let gate = await agent(testGatePrompt(), { label: 'tests:' + unit.key, phase: stage.phase, schema: GATE, effort: 'low' })
    if (!gate || !gate.ok) {
      log('Юнит ' + unit.key + ': тесты красные — раунд починки')
      await agent(fixPrompt(unit, [], 'тесты/стек красные: ' + (gate ? gate.summary : 'нет данных')), { label: 'fix-tests:' + unit.key, phase: stage.phase })
      gate = await agent(testGatePrompt(), { label: 'tests2:' + unit.key, phase: stage.phase, schema: GATE, effort: 'low' })
      if (!gate || !gate.ok) return { stopped_at: unit.key, reason: 'тесты не зазеленели после починки: ' + (gate ? gate.summary : ''), done }
    }

    let blocking = []
    if (unit.reviewers.length) {
      for (let round = 0; round <= 2; round++) {
        const reviews = await parallel(unit.reviewers.map(rt => () =>
          agent(reviewPrompt(unit, round + 1), { label: 'review' + (round + 1) + ':' + unit.key + ':' + rt.replace('ecc:', ''), phase: stage.phase, agentType: rt, schema: FINDINGS })
        ))
        blocking = reviews.filter(Boolean).flatMap(r => r.findings)
          .filter(f => f.severity === 'CRITICAL' || f.severity === 'HIGH')
        log('Юнит ' + unit.key + ': ревью раунд ' + (round + 1) + ' — блокирующих: ' + blocking.length)
        if (!blocking.length) break
        if (round === 2) return { stopped_at: unit.key, reason: 'CRITICAL/HIGH остались после 2 раундов фиксов', findings: blocking, done }
        await agent(fixPrompt(unit, blocking, 'ревью раунд ' + (round + 1)), { label: 'fix' + (round + 1) + ':' + unit.key, phase: stage.phase })
        const regate = await agent(testGatePrompt(), { label: 'retest' + (round + 1) + ':' + unit.key, phase: stage.phase, schema: GATE, effort: 'low' })
        if (!regate || !regate.ok) return { stopped_at: unit.key, reason: 'тесты сломались после фиксов: ' + (regate ? regate.summary : ''), done }
      }
    }

    const commit = await agent(commitPrompt(unit, stage.branch), { label: 'commit:' + unit.key, phase: stage.phase, schema: GATE, effort: 'low' })
    if (!commit || !commit.ok) return { stopped_at: unit.key, reason: 'коммит: ' + (commit ? commit.summary : 'commit agent failed'), done }
    done.push({ unit: unit.key, branch: stage.branch, commit: commit.summary })
    log('Юнит ' + unit.key + ' закоммичен: ' + commit.summary)
  }
}

return { completed: done, note: 'Отчёты этапов — docs/live-trading/stage-*-report.md; ветки live/stage-N мержит пользователь.' }
