import React from "react"
import { AlertCircle, CheckCircle2, Info } from "lucide-react"

type Tone = "error" | "success" | "info"

const ICONS = { error: AlertCircle, success: CheckCircle2, info: Info }

/** Inline message shown in place of browser alert() popups. */
export const Notice: React.FC<{ tone?: Tone; children: React.ReactNode; onDismiss?: () => void }> = ({
  tone = "error",
  children,
  onDismiss,
}) => {
  const Icon = ICONS[tone]
  return (
    <div className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <Icon size={18} aria-hidden="true" />
      <div className="notice-body">{children}</div>
      {onDismiss && (
        <button type="button" className="notice-dismiss" onClick={onDismiss} aria-label="Dismiss message">
          ×
        </button>
      )}
    </div>
  )
}
export default Notice
