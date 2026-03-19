import { useEffect, useState } from "react";
import { CheckCircle, AlertTriangle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

interface ToastMessage {
  id: number;
  type: ToastType;
  text: string;
}

let toastId = 0;
let addToastFn: ((type: ToastType, text: string) => void) | null = null;

export function toast(type: ToastType, text: string) {
  addToastFn?.(type, text);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    addToastFn = (type, text) => {
      const id = ++toastId;
      setToasts((t) => [...t, { id, type, text }]);
      setTimeout(() => setToasts((t) => t.filter((m) => m.id !== id)), 4000);
    };
    return () => { addToastFn = null; };
  }, []);

  const icons = {
    success: <CheckCircle size={16} />,
    error: <AlertTriangle size={16} />,
    info: <Info size={16} />,
  };

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {icons[t.type]}
          <span>{t.text}</span>
          <button className="toast-close" onClick={() => setToasts((ts) => ts.filter((m) => m.id !== t.id))}>
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
