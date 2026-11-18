export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 36 36" aria-hidden="true">
        <circle cx="15" cy="15" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx="15" cy="15" r="3.5" className="fill-primary" />
        <line x1="22.5" y1="22.5" x2="31" y2="31" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className="text-[15px] font-semibold">Exin Lab Search</span>
    </span>
  )
}
