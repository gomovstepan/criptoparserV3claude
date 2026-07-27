import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'
import Button from './Button'

interface Props {
  children: ReactNode
}
interface State {
  error: Error | null
}

/** Перехватывает ошибки рендера дочерних компонентов и показывает fallback
 *  вместо «белого экрана». Кнопка сбрасывает состояние / перезагружает. */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Логируем в консоль — в проде здесь был бы вызов error-reporting сервиса.
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger/15 text-danger">
            <AlertTriangle size={22} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-lg font-semibold text-ink">Что-то пошло не так</h2>
            <p className="mt-1 max-w-md break-words text-sm text-muted">{this.state.error.message}</p>
          </div>
          <Button
            variant="primary"
            onClick={() => {
              this.setState({ error: null })
              window.location.reload()
            }}
          >
            <RotateCcw size={15} aria-hidden="true" />
            Перезагрузить
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
