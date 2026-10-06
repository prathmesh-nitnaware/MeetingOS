import React, { useEffect, useId, useRef } from "react"
import { X } from "lucide-react"

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  footer?: React.ReactNode
  /** Wider layout for content-heavy dialogs. */
  wide?: boolean
}

/** Accessible dialog: Escape closes it, focus moves into it and returns afterwards. */
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer, wide }) => {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener("keydown", onKey)
    const first = dialogRef.current?.querySelector<HTMLElement>(
      "input, select, textarea, button:not([data-close]), [href], [tabindex]:not([tabindex='-1'])"
    )
    ;(first ?? dialogRef.current)?.focus()
    return () => {
      document.removeEventListener("keydown", onKey)
      previouslyFocused?.focus?.()
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        ref={dialogRef}
        className={`modal-content${wide ? " modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 id={titleId} className="card-title" style={{ margin: 0 }}>
            {title}
          </h3>
          <button
            type="button"
            className="btn btn-outline icon-btn"
            onClick={onClose}
            aria-label="Close dialog"
            data-close
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}
export default Modal
