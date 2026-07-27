import { useEffect } from 'react'

const SUFFIX = 'ArbitrageHub'

/**
 * Заголовок вкладки под текущий раздел.
 * Раньше во всех разделах был один статичный <title>: вкладки не различались,
 * а история браузера состояла из одинаковых записей.
 */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · ${SUFFIX}`
  }, [title])
}
