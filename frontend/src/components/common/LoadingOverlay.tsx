interface LoadingOverlayProps {
  message?: string;
}

export function LoadingOverlay({ message = "Running analysis..." }: LoadingOverlayProps) {
  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  );
}
